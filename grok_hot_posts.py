#!/usr/bin/env python3
"""
X 热门帖子搜集器 - 通过 Grok AI 获取
复用 auto_publish_uc.py 的 UC driver 基础设施
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置
PROFILE_DIR = os.environ.get("XPOST_PROFILE_DIR")
if PROFILE_DIR:
    USER_DATA_DIR = Path(PROFILE_DIR)
else:
    USER_DATA_DIR = Path(__file__).parent / "chrome_data_mirror"

GROK_URL = "https://x.com/i/grok"

# Grok 提示词构建器
def build_grok_prompt(topics: list, count: int, hours: int, tags: list = None):
    """动态构建 Grok 提示词
    
    Args:
        topics: 主题列表，如 ["AI", "科技", "开源Github"]
        count: 帖子数量
        hours: 时间范围（小时）
        tags: 可选的内容标签列表
    
    Returns:
        str: 格式化的 Grok 提示词
    """
    topics_str = "、".join(topics)
    
    # 如果提供了 tags，使用 tags；否则使用默认描述
    if tags:
        tags_str = "、".join(tags)
    else:
        # 默认标签基于主题生成
        tags_str = f"{topics_str}相关的技术突破、进展、动态、热门项目等"
    
    return f"""请在 X (Twitter) 上搜索过去 {hours} 小时内关于【{topics_str}】的真实热门x帖子，找出浏览量最高的{count} 条。

要求：
- 必须是真实存在的X帖子,不要编造,必须是英文帖子
- 内容范围：{tags_str}
- 按浏览量从高到低排序

请直接返回 JSON 数组，每条帖子包含以下 7 个字段：
time（发帖时间）、author（@用户名）、summary（中文摘要50字内）、views（浏览量）、likes（点赞数）、reposts（转发数）、url（帖子链接）

只返回 JSON 数组，不要任何解释。"""


def _cleanup_chrome_profile(profile_dir: Path, quiet=False):
    """清理 Chrome 用户数据目录的残留锁文件和僵尸进程"""
    import subprocess as sp

    # 1. 清理锁文件
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_file = profile_dir / lock_name
        if lock_file.exists() or lock_file.is_symlink():
            try:
                lock_file.unlink()
                if not quiet:
                    print(f"   🧹 清理残留锁: {lock_name}")
            except Exception:
                pass

    # 2. 杀掉使用该 profile 的旧 chromedriver 进程（排除自身）
    try:
        my_pid = str(os.getpid())
        pattern = f"user-data-dir={profile_dir}"
        result = sp.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=3
        )
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            pid = pid.strip()
            if pid and pid != my_pid:
                try:
                    # 先尝试温和结束，避免误伤时直接硬杀
                    sp.run(["kill", "-15", pid], timeout=2)
                    if not quiet:
                        print(f"   🧹 终止残留进程: PID {pid}")
                except Exception:
                    pass
    except Exception:
        pass


def create_driver(quiet=False):
    """创建 undetected Chrome 驱动"""
    if not quiet:
        print("🌐 启动浏览器...")
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 清理残留锁文件和僵尸进程
    _cleanup_chrome_profile(USER_DATA_DIR, quiet=quiet)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")

    version_main_env = os.environ.get("XPOST_CHROME_VERSION_MAIN")
    try:
        version_main = int(version_main_env) if version_main_env else 145
    except ValueError:
        version_main = 145

    # 优先使用本地已缓存的 ChromeDriver（避免每次从网络下载）
    uc_driver_path = Path.home() / "Library" / "Application Support" / "undetected_chromedriver" / "undetected_chromedriver"
    # 备份路径：项目内
    local_driver_path = Path(__file__).parent / "chromedriver"
    
    driver_exe = None
    if uc_driver_path.exists() and uc_driver_path.stat().st_size > 1000:
        driver_exe = str(uc_driver_path)
    elif local_driver_path.exists() and local_driver_path.stat().st_size > 1000:
        driver_exe = str(local_driver_path)
    
    kwargs = dict(
        options=options,
        use_subprocess=True,
        version_main=version_main,
    )
    if driver_exe:
        kwargs["driver_executable_path"] = driver_exe
        if not quiet:
            print(f"   📦 使用本地 ChromeDriver")

    driver = uc.Chrome(**kwargs)
    if not quiet:
        print("✅ 浏览器已启动")
    return driver


def random_delay(min_ms=500, max_ms=2000):
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def start_new_conversation(driver, quiet=False):
    """确保在全新的 Grok 对话中开始，清除历史上下文"""
    if not quiet:
        print("🆕 新建 Grok 对话...")
    
    # 方法 1：尝试点击 "New chat" 按钮
    new_chat_selectors = [
        'a[href="/i/grok"]',                          # 侧栏 Grok 链接
        'button[aria-label*="New"]',                    # New chat 按钮
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
            els = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in els:
                if el.is_displayed():
                    el.click()
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
        driver.get(GROK_URL)
        random_delay(3000, 5000)
    
    # 等待页面加载，确认输入框可用
    input_selectors = [
        'textarea[placeholder]',
        'div[contenteditable="true"]',
        'textarea',
    ]
    for selector in input_selectors:
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            if not quiet:
                print("   ✅ 新对话就绪")
            return True
        except TimeoutException:
            continue
    
    if not quiet:
        print("   ⚠️  无法确认新对话状态，继续尝试...")
    return True


def wait_for_grok_response(driver, timeout=300, quiet=False):
    """等待 Grok 生成完毕"""
    if not quiet:
        print("⏳ 等待 Grok 回复...")
    time.sleep(3)

    start = time.time()
    last_text = ""
    stable_count = 0
    MIN_WAIT = 15  # 最少等待 15 秒（Grok Thinking 需要时间搜索）

    while time.time() - start < timeout:
        elapsed = int(time.time() - start)

        # 1. 优先检查回复内容是否可解析为 JSON（避免误判一直生成）
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
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    t = els[-1].text.strip()
                    if len(t) > len(current_text):
                        current_text = t
            except Exception:
                continue

        # 第二优先级：markdown 容器（Grok Thinking 常用）
        if not current_text or len(current_text) < 100:
            for sel in ['div.markdown', 'div[class*="markdown"]']:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        t = els[-1].text.strip()
                        if len(t) > len(current_text) and ('[' in t or '{' in t):
                            current_text = t
                except Exception:
                    continue

        # 第三优先级：JS 提取页面文本中的 JSON 片段
        if not current_text or len(current_text) < 100:
            try:
                body_text = driver.execute_script("return document.body.innerText")
                if body_text and '"author"' in body_text and '"url"' in body_text:
                    # 页面中已出现 JSON 字段标志
                    start_idx = body_text.find('[')
                    end_idx = body_text.rfind(']')
                    if start_idx != -1 and end_idx > start_idx:
                        current_text = body_text[start_idx:end_idx + 1]
            except Exception:
                pass

        if current_text and len(current_text) > 30 and parse_json_from_text(current_text):
            if current_text == last_text:
                stable_count += 1
                if stable_count >= 1:  # 连续稳定 1 次即可视为完成
                    if not quiet:
                        print(f"✅ Grok 回复完成 ({elapsed}s, {len(current_text)} 字符)")
                    return True
            else:
                stable_count = 0
                last_text = current_text

        # 2. 检查是否还在生成（尽量使用较精准选择器，减少误判）
        still_generating = False
        try:
            gen_selectors = [
                'button[aria-label*="Stop"]',
                'button[aria-label*="stop"]',
                'button[data-testid*="stop"]',
            ]
            for sel in gen_selectors:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els and any(e.is_displayed() for e in els):
                    still_generating = True
                    break
        except Exception:
            pass

        if still_generating:
            stable_count = 0
            if elapsed % 10 == 0 and not quiet:
                print(f"   ⏳ 生成中... ({elapsed}s)")
            time.sleep(2)
            continue

        # 最少等待时间未到，继续等
        if elapsed < MIN_WAIT:
            time.sleep(2)
            continue

        time.sleep(2)

    if not quiet:
        print(f"⚠️  等待超时 ({timeout}s)，尝试提取当前内容")
    return False


def extract_grok_response(driver):
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
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                text = elements[-1].text.strip()
                if len(text) > 50 and ('[' in text or '{' in text):
                    return text
        except Exception:
            continue

    # 兜底：尝试获取 Grok 回复区域（排除导航元素）
    fallback_selectors = [
        'div.markdown',
        'div[class*="markdown"]',
    ]
    for selector in fallback_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                text = elements[-1].text.strip()
                if len(text) > 50:
                    return text
        except Exception:
            continue

    # 最后兜底
    try:
        body = driver.execute_script("return document.body.innerText")
        return body
    except Exception:
        return ""


def send_prompt_to_grok(driver, prompt, quiet=False):
    """在 Grok 对话框中输入提示词并发送"""
    if not quiet:
        print("📝 输入提示词...")

    # 查找输入框
    input_selectors = [
        'textarea[placeholder]',
        'div[contenteditable="true"]',
        'textarea',
        'input[type="text"]',
    ]

    input_el = None
    for selector in input_selectors:
        try:
            input_el = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            if input_el:
                break
        except TimeoutException:
            continue

    if not input_el:
        if not quiet:
            print("❌ 找不到 Grok 输入框")
        return False

    # 点击输入框获取焦点
    input_el.click()
    random_delay(300, 600)

    # 先清空输入框（防止历史文本残留）
    from selenium.webdriver.common.action_chains import ActionChains
    # macOS 用 Command+A 全选，然后删除（用 ActionChains 确保组合键可靠）
    ActionChains(driver).key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).perform()
    random_delay(100, 200)
    ActionChains(driver).send_keys(Keys.BACKSPACE).perform()
    random_delay(300, 500)

    # 使用剪贴板粘贴输入（避免 send_keys 遇到换行符触发提交）
    import subprocess as sp
    # 将提示词写入 macOS 剪贴板
    proc = sp.Popen(['pbcopy'], stdin=sp.PIPE)
    proc.communicate(prompt.encode('utf-8'))
    random_delay(200, 400)
    # Cmd+V 粘贴
    input_el.send_keys(Keys.COMMAND, 'v')
    random_delay(800, 1500)

    # 发送：优先点击按钮，兜底用 Enter
    send_selectors = [
        'button[data-testid="send"]',
        'button[data-testid="sendButton"]',
        'button[aria-label*="Send"]',
        'button[aria-label*="send"]',
        'button[aria-label*="发送"]',
        'button[aria-label*="Submit"]',
        # Grok 的发送按钮可能是带 SVG 箭头的 button
        'button svg[viewBox] ~ *',
    ]

    sent = False
    for selector in send_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            if btn.is_displayed():
                btn.click()
                sent = True
                if not quiet:
                    print(f"✅ 提示词已发送（按钮: {selector}）")
                break
        except (NoSuchElementException, Exception):
            continue

    if not sent:
        # 尝试找输入框旁边/父容器内的 button
        try:
            parent = input_el.find_element(By.XPATH, "./ancestor::form | ./ancestor::div[contains(@class,'input')]")
            btns = parent.find_elements(By.TAG_NAME, "button")
            for btn in btns:
                if btn.is_displayed():
                    btn.click()
                    sent = True
                    if not quiet:
                        print("✅ 提示词已发送（父容器按钮）")
                    break
        except Exception:
            pass

    if not sent:
        # 最终兜底：Enter 键发送（ActionChains 已在上方 import）
        ActionChains(driver).key_down(Keys.RETURN).key_up(Keys.RETURN).perform()
        if not quiet:
            print("✅ 提示词已发送（Enter）")

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

    # 扫描并提取第一个可解析的 JSON 数组（可跳过前后噪声 [] 文本）
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
                  topics=None, hours=None):
    """输出结果
    
    Args:
        posts: 解析后的帖子列表
        raw_text: Grok 原始回复
        output_dir: 输出目录
        json_only: 仅输出 JSON 到 stdout
        quiet: 静默模式
        topics: 搜索主题列表
        hours: 时间范围
    """
    # 按时间倒序排序（最新在前）
    if posts:
        def _parse_time(post):
            t = post.get("time", "")
            # 尝试解析标准格式 "2026-02-13 08:16:31"
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(t, fmt)
                except (ValueError, TypeError):
                    continue
            # 无法解析则排最后
            return datetime.min
        posts.sort(key=_parse_time, reverse=True)

    if json_only:
        # 类似 xpost.py，直接输出 JSON 到 stdout
        result = {
            "ok": posts is not None and len(posts) > 0,
            "count": len(posts) if posts else 0,
            "topics": topics or [],
            "hours": hours,
            "posts": posts or []
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 否则保存文件 + 打印（原有逻辑）
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

        # 打印结果（除非 quiet）
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
            print(f"   请查看原始文件确认 Grok 回复内容")


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
  
  # 仅输出 JSON（用于 Agent/脚本集成）
  %(prog)s --json-only
""")
    
    # 核心参数
    parser.add_argument("-n", "--count", type=int, default=10,
                       help="帖子数量（默认: 10）")
    parser.add_argument("--hours", type=int, default=72,
                       help="时间范围，单位小时（默认: 72）")
    parser.add_argument("--topics", nargs="+", 
                       default=["AI", "科技", "开源Github"],
                       help="搜索主题（默认: AI 科技 开源Github）")
    parser.add_argument("--tags", nargs="*",
                       help="内容标签，用于细化搜索")
    
    # 输出参数
    parser.add_argument("--output", default="./hot_posts_output",
                       help="输出目录（默认: ./hot_posts_output）")
    parser.add_argument("--json-only", action="store_true",
                       help="仅输出 JSON 到 stdout，不保存文件")
    parser.add_argument("-q", "--quiet", action="store_true",
                       help="静默模式，减少输出")
    
    # 浏览器参数
    parser.add_argument("--timeout", type=int, default=300,
                        help="等待 Grok 回复超时，单位秒（默认: 300，Grok Thinking 需要较长时间）")
    parser.add_argument("--prompt", 
                       help="自定义 Grok 提示词（高级用法，会覆盖 topics/count/hours）")
    
    args = parser.parse_args()
    if args.json_only:
        # 机器模式：仅输出 JSON，禁止日志污染 stdout
        args.quiet = True

    # 构建提示词
    if args.prompt:
        # 用户提供了自定义提示词
        prompt = args.prompt
    else:
        # 使用参数化构建
        prompt = build_grok_prompt(
            topics=args.topics,
            count=args.count,
            hours=args.hours,
            tags=args.tags
        )

    driver = None
    try:
        driver = create_driver(quiet=args.quiet)

        # 打开 Grok
        if not args.quiet:
            print(f"🔗 打开 Grok: {GROK_URL}")
        driver.get(GROK_URL)
        random_delay(3000, 5000)

        # 检查是否需要登录
        if "login" in driver.current_url.lower():
            if not args.quiet:
                print("⚠️  需要登录，请在浏览器中手动登录...")
                print("   登录后脚本将自动继续（超时 300 秒）")
            start = time.time()
            while time.time() - start < 300:
                if "login" not in driver.current_url.lower():
                    if not args.quiet:
                        print("✅ 登录成功")
                    driver.get(GROK_URL)
                    random_delay(3000, 5000)
                    break
                time.sleep(3)
            else:
                if args.json_only:
                    print(json.dumps({"ok": False, "error": "登录超时"}, ensure_ascii=False))
                else:
                    print("❌ 登录超时")
                return 1

        # 新建对话（清除历史上下文）
        start_new_conversation(driver, quiet=args.quiet)

        # 发送提示词
        if not send_prompt_to_grok(driver, prompt, quiet=args.quiet):
            if args.json_only:
                print(json.dumps({"ok": False, "error": "发送提示词失败"}, ensure_ascii=False))
            else:
                print("❌ 发送提示词失败")
            return 2

        # 等待回复
        completed = wait_for_grok_response(driver, timeout=args.timeout, quiet=args.quiet)
        if not completed and not args.quiet:
            print("⚠️  Grok 回复等待超时，尝试提取当前内容")

        # 提取回复
        raw_text = extract_grok_response(driver)
        if not raw_text:
            if args.json_only:
                print(json.dumps({"ok": False, "error": "未获取到 Grok 回复"}, ensure_ascii=False))
            else:
                print("❌ 未获取到 Grok 回复")
            return 3

        # 解析 JSON
        posts = parse_json_from_text(raw_text)

        # 输出结果
        output_results(
            posts, 
            raw_text, 
            args.output,
            json_only=args.json_only,
            quiet=args.quiet,
            topics=args.topics,
            hours=args.hours
        )
        
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
        if driver:
            if not args.quiet:
                print("\n🔒 关闭浏览器...")
            driver.quit()


if __name__ == "__main__":
    sys.exit(main())
