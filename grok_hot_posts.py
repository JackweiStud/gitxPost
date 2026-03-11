#!/usr/bin/env python3
"""
X 热门帖子搜集器 - 通过 Grok AI 获取
使用共享浏览器会话层 (browser_cdp_session.py)
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

# 导入共享浏览器会话层
from browser_cdp_session import ChromeCDPSession, create_session

try:
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
    from patchright.sync_api import Page
except Exception:
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Page = object

# 配置
PROFILE_DIR = os.environ.get("XPOST_PROFILE_DIR")
if PROFILE_DIR:
    USER_DATA_DIR = Path(PROFILE_DIR)
else:
    USER_DATA_DIR = Path(__file__).parent / "chrome_data_mirror"

GROK_URL = "https://x.com/i/grok"


def _log_progress(msg):
    """输出进度信息到 stderr（不污染 stdout 的 JSON 输出）"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def build_grok_prompt(topics: list, count: int, hours: int, tags: list = None):
    """动态构建 Grok 提示词"""
    topics_str = "、".join(topics)
    
    if tags:
        tags_str = "、".join(tags)
    else:
        tags_str = f"{topics_str}相关的技术突破、进展、动态、热门项目等"
    
    return f"""请在 X (Twitter) 上搜索过去 {hours} 小时内关于{topics_str}的真实热门x帖子，找出浏览量最高的{count}条。

要求：
- 必须是真实存在的X帖子,不要编造,必须是英文帖子
- 内容范围：{tags_str}
- 按浏览量从高到低排序

请直接返回 JSON 数组，每条帖子包含以下 7 个字段：
time（发帖时间）、author（@用户名）、summary（中文摘要50字内）、views（浏览量）、likes（点赞数）、reposts（转发数）、url（帖子链接）

只返回 JSON 数组，不要任何解释。"""


def create_session_and_page(quiet=False):
    """创建浏览器会话和页面（使用共享会话层）"""
    _log_progress("🌐 启动浏览器...")
    if not quiet:
        print("🌐 启动浏览器...")
    
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 使用共享浏览器会话层
    session = create_session(profile_dir=USER_DATA_DIR)
    browser, context, page = session.start()
    
    _log_progress("✅ 浏览器已启动")
    if not quiet:
        print("✅ 浏览器已启动")
    
    return session, page


def random_delay(min_ms=500, max_ms=2000):
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def start_new_conversation(page: Page, quiet=False):
    """确保在全新的 Grok 对话中开始，清除历史上下文"""
    _log_progress("🆕 新建 Grok 对话...")
    if not quiet:
        print("🆕 新建 Grok 对话...")
    
    # 方法 1：尝试点击 "New chat" 按钮
    new_chat_selectors = [
        'a[href="/i/grok"]',
        'button[aria-label*="New"]',
        'button[aria-label*="new"]',
        'button[aria-label*="新"]',
        'a[aria-label*="New chat"]',
        'a[aria-label*="new chat"]',
        'button[data-testid="new-chat"]',
        'button[data-testid="newChat"]',
    ]
    
    clicked = False
    for selector in new_chat_selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            for i in range(count):
                element = locator.nth(i)
                if element.is_visible():
                    element.click()
                    clicked = True
                    if not quiet:
                        print(f"   ✅ 点击了新建对话按钮")
                    random_delay(1500, 2500)
                    break
        except Exception:
            continue
        if clicked:
            break
    
    # 方法 2：如果没找到按钮，直接导航到 Grok 首页（强制刷新）
    if not clicked:
        if not quiet:
            print("   🔄 通过导航强制新建对话...")
        page.goto(GROK_URL, wait_until="domcontentloaded", timeout=60000)
        random_delay(3000, 5000)
    
    # 等待页面加载，确认输入框可用
    input_selectors = [
        'textarea[placeholder]',
        'div[contenteditable="true"]',
        'textarea',
    ]
    for selector in input_selectors:
        try:
            page.wait_for_selector(selector, state="visible", timeout=10000)
            if not quiet:
                print("   ✅ 新对话就绪")
            return True
        except PlaywrightTimeoutError:
            continue
    
    if not quiet:
        print("   ⚠️  无法确认新对话状态，继续尝试...")
    return True


def wait_for_grok_response(page: Page, timeout=300, quiet=False):
    """等待 Grok 生成完毕"""
    _log_progress(f"⏳ 等待 Grok 回复（超时: {timeout}s）...")
    if not quiet:
        print("⏳ 等待 Grok 回复...")
    time.sleep(3)

    start = time.time()
    last_text = ""
    stable_count = 0
    MIN_WAIT = 15

    while time.time() - start < timeout:
        elapsed = int(time.time() - start)

        # 1. 优先检查回复内容是否可解析为 JSON
        current_text = ""
        
        # 第一优先级：code/pre 代码块
        code_selectors = [
            'code.language-json',
            'pre code',
            'div[data-testid="markdown-code-block"]',
            'pre',
        ]
        for sel in code_selectors:
            try:
                locator = page.locator(sel)
                count = locator.count()
                if count > 0:
                    t = locator.nth(count - 1).text_content()
                    if t and len(t) > len(current_text):
                        current_text = t.strip()
            except Exception:
                continue

        # 第二优先级：markdown 容器
        if not current_text or len(current_text) < 100:
            for sel in ['div.markdown', 'div[class*="markdown"]']:
                try:
                    locator = page.locator(sel)
                    count = locator.count()
                    if count > 0:
                        t = locator.nth(count - 1).text_content()
                        if t and len(t) > len(current_text) and ('[' in t or '{' in t):
                            current_text = t.strip()
                except Exception:
                    continue

        # 第三优先级：JS 提取页面文本中的 JSON 片段
        if not current_text or len(current_text) < 100:
            try:
                body_text = page.evaluate("() => document.body.innerText")
                if body_text and '"author"' in body_text and '"url"' in body_text:
                    start_idx = body_text.find('[')
                    end_idx = body_text.rfind(']')
                    if start_idx != -1 and end_idx > start_idx:
                        current_text = body_text[start_idx:end_idx + 1]
            except Exception:
                pass

        if current_text and len(current_text) > 30 and parse_json_from_text(current_text):
            if current_text == last_text:
                stable_count += 1
                if stable_count >= 1:
                    _log_progress(f"✅ Grok 回复完成 ({elapsed}s, {len(current_text)} 字符)")
                    if not quiet:
                        print(f"✅ Grok 回复完成 ({elapsed}s, {len(current_text)} 字符)")
                    return True
            else:
                stable_count = 0
                last_text = current_text

        # 2. 检查是否还在生成
        still_generating = False
        try:
            gen_selectors = [
                'button[aria-label*="Stop"]',
                'button[aria-label*="stop"]',
                'button[data-testid*="stop"]',
            ]
            for sel in gen_selectors:
                locator = page.locator(sel)
                if locator.count() > 0 and locator.first.is_visible():
                    still_generating = True
                    break
        except Exception:
            pass

        if still_generating:
            stable_count = 0
            if elapsed % 30 == 0:
                _log_progress(f"   ⏳ Grok 生成中... ({elapsed}s / {timeout}s)")
            if elapsed % 10 == 0 and not quiet:
                print(f"   ⏳ 生成中... ({elapsed}s)")
            time.sleep(2)
            continue

        # 最少等待时间未到，继续等
        if elapsed < MIN_WAIT:
            time.sleep(2)
            continue

        time.sleep(2)

    _log_progress(f"⚠️  等待超时 ({timeout}s)，尝试提取当前内容")
    if not quiet:
        print(f"⚠️  等待超时 ({timeout}s)，尝试提取当前内容")
    return False


def extract_grok_response(page: Page):
    """提取 Grok 最后一条回复的文本"""
    # 优先提取 JSON 代码块
    json_selectors = [
        'code.language-json',
        'pre code',
        'div[data-testid="markdown-code-block"]',
        'pre',
    ]

    for selector in json_selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            if count > 0:
                text = locator.nth(count - 1).text_content()
                if text and len(text) > 50 and ('[' in text or '{' in text):
                    return text.strip()
        except Exception:
            continue

    # 兜底：尝试获取 Grok 回复区域
    fallback_selectors = [
        'div.markdown',
        'div[class*="markdown"]',
    ]
    for selector in fallback_selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            if count > 0:
                text = locator.nth(count - 1).text_content()
                if text and len(text) > 50:
                    return text.strip()
        except Exception:
            continue

    # 最后兜底
    try:
        body = page.evaluate("() => document.body.innerText")
        return body
    except Exception:
        return ""


def send_prompt_to_grok(page: Page, prompt, quiet=False):
    """在 Grok 对话框中输入提示词并发送"""
    _log_progress("📝 输入提示词...")
    if not quiet:
        print("📝 输入提示词...")

    # 查找输入框
    input_selectors = [
        'textarea[placeholder]',
        'div[contenteditable="true"]',
        'textarea',
        'input[type="text"]',
    ]

    input_locator = None
    for selector in input_selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                input_locator = locator.first
                input_locator.wait_for(state="visible", timeout=10000)
                break
        except PlaywrightTimeoutError:
            continue

    if not input_locator:
        if not quiet:
            print("❌ 找不到 Grok 输入框")
        return False

    # 获取焦点（使用 focus 避免被遮挡元素阻止）
    try:
        input_locator.focus()
    except Exception:
        # 如果 focus 失败，尝试强制点击
        input_locator.click(force=True)
    random_delay(300, 600)

    # 先清空输入框
    try:
        page.keyboard.press("Meta+A")
        random_delay(100, 200)
        page.keyboard.press("Backspace")
        random_delay(300, 500)
    except Exception:
        pass

    # 使用剪贴板粘贴输入
    import subprocess as sp
    proc = sp.Popen(['pbcopy'], stdin=sp.PIPE)
    proc.communicate(prompt.encode('utf-8'))
    random_delay(200, 400)
    
    # Cmd+V 粘贴
    page.keyboard.press("Meta+V")
    random_delay(800, 1500)

    # 发送：优先点击按钮
    send_selectors = [
        'button[data-testid="send"]',
        'button[data-testid="sendButton"]',
        'button[aria-label*="Send"]',
        'button[aria-label*="send"]',
        'button[aria-label*="发送"]',
        'button[aria-label*="Submit"]',
    ]

    sent = False
    for selector in send_selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0 and locator.first.is_visible():
                locator.first.click()
                sent = True
                if not quiet:
                    print(f"✅ 提示词已发送（按钮: {selector}）")
                break
        except Exception:
            continue

    if not sent:
        # 兜底：Enter 键发送
        page.keyboard.press("Enter")
        if not quiet:
            print("✅ 提示词已发送（Enter）")

    _log_progress("✅ 提示词已发送，等待 Grok 响应...")
    return True


def parse_json_from_text(text):
    """从 Grok 回复中提取 JSON 数组"""
    import re

    # 找 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 扫描并提取第一个可解析的 JSON 数组
    decoder = json.JSONDecoder()
    starts = [m.start() for m in re.finditer(r"\[", text)]
    for start_idx in starts:
        candidate = text[start_idx:].lstrip()
        try:
            obj, _ = decoder.raw_decode(candidate)
            if isinstance(obj, list):
                return obj
        except json.JSONDecodeError:
            continue

    # 兼容 innerText 破坏格式后再尝试
    normalized = re.sub(r'"\s*\n\s*(@\w+)\s*\n\s*"', r'"\1"', text)
    normalized = re.sub(r':\s*"\s*\n\s*', ': "', normalized)
    normalized = re.sub(r'\s*\n\s*"(\s*[,}])', r'"\1', normalized)
    normalized = re.sub(r'\n\s*\n', '\n', normalized)
    starts = [m.start() for m in re.finditer(r"\[", normalized)]
    for start_idx in starts:
        candidate = normalized[start_idx:].lstrip()
        try:
            obj, _ = decoder.raw_decode(candidate)
            if isinstance(obj, list):
                return obj
        except json.JSONDecodeError:
            continue

    return None


def output_results(posts, raw_text, output_dir, json_only=False, quiet=False, 
                  topics=None, hours=None, count=10):
    """输出结果"""
    # 排序：按浏览量降序
    if posts:
        def _parse_time(post):
            t = post.get("time", "")
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(t, fmt)
                except (ValueError, TypeError):
                    continue
            return datetime.min
        posts.sort(key=lambda p: (
            int(p.get("views", 0) or 0),
            _parse_time(p),
        ), reverse=True)
        posts = posts[:count]

    if json_only:
        result = {
            "ok": posts is not None and len(posts) > 0,
            "count": len(posts) if posts else 0,
            "topics": topics or [],
            "hours": hours,
            "posts": posts or []
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 保存文件 + 打印
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存原始回复
    raw_file = output_dir / f"grok_raw_{timestamp}.txt"
    raw_file.write_text(raw_text, encoding="utf-8")

    # 保存 JSON
    if posts:
        json_file = output_dir / f"hot_posts_{timestamp}.json"
        json_file.write_text(
            json.dumps(posts, ensure_ascii=False, indent=2),
            encoding="utf-8")

        if not quiet:
            print(f"\n{'='*60}")
            print(f"✅ 搜集完成！共获取 {len(posts)} 条热门帖子")
            print(f"{'='*60}")
            for i, post in enumerate(posts, 1):
                time_str = post.get("time", "未知时间")
                author = post.get("author", "未知")
                summary = post.get("summary", "")
                likes = post.get("likes", "N/A")
                reposts = post.get("reposts", post.get("retweets", "N/A"))
                views = post.get("views", "N/A")
                url = post.get("url", "")
                print(f"\n  {i}. {author} · {time_str}")
                print(f"     {summary}")
                print(f"     👁 {views}  ❤️ {likes}  🔁 {reposts}")
                print(f"     🔗 {url}")
            print(f"\n{'='*60}")
            print(f"📄 原始回复: {raw_file}")
            print(f"📊 JSON 文件: {json_file}")
            print(f"{'='*60}")
    else:
        if not quiet:
            print(f"\n⚠️  未能解析出结构化数据")
            print(f"📄 原始回复已保存: {raw_file}")


def main():
    parser = argparse.ArgumentParser(
        description="通过 Grok 获取 X 热门帖子",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  # 默认：10条，72小时，AI+科技+开源Github
  %(prog)s
  
  # 自定义数量和时间
  %(prog)s --count 20 --hours 24
  
  # 自定义主题
  %(prog)s --topics "大模型" "机器学习" --count 15
  
  # 仅输出 JSON
  %(prog)s --json-only
""")
    
    parser.add_argument("-n", "--count", type=int, default=10,
                       help="帖子数量（默认: 10）")
    parser.add_argument("--hours", type=int, default=72,
                       help="时间范围，单位小时（默认: 72）")
    parser.add_argument("--topics", nargs="+", 
                       default=["AI", "科技", "开源Github"],
                       help="搜索主题（默认: AI 科技 开源Github）")
    parser.add_argument("--tags", nargs="*",
                       help="内容标签")
    parser.add_argument("--output", default="./hot_posts_output",
                       help="输出目录（默认: ./hot_posts_output）")
    parser.add_argument("--json-only", action="store_true",
                       help="仅输出 JSON 到 stdout")
    parser.add_argument("-q", "--quiet", action="store_true",
                       help="静默模式")
    parser.add_argument("--timeout", type=int, default=300,
                        help="等待超时，单位秒（默认: 300）")
    parser.add_argument("--prompt", 
                       help="自定义 Grok 提示词")
    
    args = parser.parse_args()
    if args.json_only:
        args.quiet = True

    # 构建提示词
    if args.prompt:
        prompt = args.prompt
    else:
        prompt = build_grok_prompt(
            topics=args.topics,
            count=args.count,
            hours=args.hours,
            tags=args.tags
        )

    session = None
    try:
        session, page = create_session_and_page(quiet=args.quiet)

        # 打开 Grok
        _log_progress(f"🔗 打开 Grok 页面...")
        if not args.quiet:
            print(f"🔗 打开 Grok: {GROK_URL}")
        page.goto(GROK_URL, wait_until="domcontentloaded", timeout=60000)
        random_delay(3000, 5000)

        # 检查是否需要登录
        current_url = page.url
        if "login" in current_url.lower():
            if not args.quiet:
                print("⚠️  需要登录，请在浏览器中手动登录...")
                print("   登录后脚本将自动继续（超时 300 秒）")
            start = time.time()
            while time.time() - start < 300:
                current_url = page.url
                if "login" not in current_url.lower():
                    if not args.quiet:
                        print("✅ 登录成功")
                    page.goto(GROK_URL, wait_until="domcontentloaded", timeout=60000)
                    random_delay(3000, 5000)
                    break
                time.sleep(3)
            else:
                if args.json_only:
                    print(json.dumps({"ok": False, "error": "登录超时"}, ensure_ascii=False))
                else:
                    print("❌ 登录超时")
                return 1

        # 新建对话
        start_new_conversation(page, quiet=args.quiet)

        # 发送提示词
        if not send_prompt_to_grok(page, prompt, quiet=args.quiet):
            if args.json_only:
                print(json.dumps({"ok": False, "error": "发送提示词失败"}, ensure_ascii=False))
            else:
                print("❌ 发送提示词失败")
            return 2

        # 等待回复
        completed = wait_for_grok_response(page, timeout=args.timeout, quiet=args.quiet)
        if not completed and not args.quiet:
            print("⚠️  Grok 回复等待超时，尝试提取当前内容")

        # 提取回复
        raw_text = extract_grok_response(page)
        if not raw_text:
            if args.json_only:
                print(json.dumps({"ok": False, "error": "未获取到 Grok 回复"}, ensure_ascii=False))
            else:
                print("❌ 未获取到 Grok 回复")
            return 3

        # 解析 JSON
        _log_progress(f"📋 解析 Grok 回复 ({len(raw_text)} 字符)...")
        posts = parse_json_from_text(raw_text)

        # 输出结果
        output_results(
            posts, 
            raw_text, 
            args.output,
            json_only=args.json_only,
            quiet=args.quiet,
            topics=args.topics,
            hours=args.hours,
            count=10
        )
        
        _log_progress(f"🏁 完成！获取 {len(posts) if posts else 0} 条帖子")
        return 0 if posts else 4

    except KeyboardInterrupt:
        if not args.json_only:
            print("\n⏹  用户中断")
        return 130
    except Exception as e:
        if args.json_only:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        else:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        return 5
    finally:
        if session:
            _log_progress("🔒 关闭浏览器...")
            if not args.quiet:
                print("\n🔒 关闭浏览器...")
            session.close()


if __name__ == "__main__":
    sys.exit(main())
