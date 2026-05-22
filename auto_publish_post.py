#!/usr/bin/env python3
"""
X Post 自动发布系统（macOS）
使用共享浏览器会话层 (browser_cdp_session.py)
"""

import argparse
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Optional

# 导入共享浏览器会话层
from browser_cdp_session import ChromeCDPSession, create_session

try:
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
    from patchright.sync_api import Locator, Page
except Exception:
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Locator = object
    Page = object

logging.basicConfig(
    filename="xpost_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = Path(os.environ.get("XPOST_PROFILE_DIR") or (BASE_DIR / "chrome_data_mirror"))
POST_URL = "https://x.com/compose/post"
LOGIN_URL = "https://x.com/i/flow/login"
HOME_URL = "https://x.com/home"
# MAX_TEXT_LENGTH = 1000 (X Premium has no limit)
MAX_IMAGES = 10
STEP_PAUSE_MS = int(os.environ.get("XPOST_STEP_PAUSE_MS", "900"))

SELECTORS = {
    "dialog": [
        'div[aria-modal="true"][role="dialog"]',
        'div[role="dialog"]',
    ],
    "textarea": [
        'div[data-testid="tweetTextarea_0"]',
        'div[data-testid="tweetTextarea_0_label"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][aria-label*="Post"]',
        '[aria-label*="Post text"]',
        'div[contenteditable="true"]',
    ],
    "file_input": [
        'input[data-testid="fileInput"]',
        'input[type="file"][accept*="image"]',
        'input[type="file"]',
    ],
    "post_button": [
        'button[data-testid="tweetButton"]',
        'button[data-testid="tweetButtonInline"]',
        'div[role="button"][data-testid="tweetButton"]',
        'div[role="button"][data-testid="tweetButtonInline"]',
        '[data-testid="tweetButton"]',
        '[data-testid="tweetButtonInline"]',
    ],
}


def validate_text_length(text: str) -> bool:
    """验证文本长度"""
    if not text.strip():
        raise ValueError("文本内容不能为空")
    return True


def validate_media(media: Optional[List[str]]) -> bool:
    """验证媒体附件"""
    if not media:
        return True
    if len(media) > MAX_IMAGES:
        raise ValueError(f"媒体数量超过 {MAX_IMAGES} 个限制（当前：{len(media)}）")
    for media_path in media:
        if not Path(media_path).exists():
            raise FileNotFoundError(f"媒体文件不存在: {media_path}")
    return True


validate_images = validate_media


class HumanBehaviorSimulator:
    """人类行为模拟器"""
    
    @staticmethod
    def random_delay(min_ms: int = 500, max_ms: int = 2000) -> None:
        time.sleep(random.uniform(min_ms, max_ms) / 1000)

    @staticmethod
    def warmup_page(page: Page) -> None:
        print("   🔥 页面预热中...")
        HumanBehaviorSimulator.random_delay(900, 1600)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        HumanBehaviorSimulator.random_delay(250, 650)
        print("   ✅ 预热完成")

    @staticmethod
    def human_type(page: Page, locator: Locator, text: str) -> None:
        locator.click()
        HumanBehaviorSimulator.random_delay(200, 600)
        for segment in _split_text_segments(text):
            locator.press_sequentially(segment, delay=random.randint(35, 95))
            if random.random() < 0.18:
                HumanBehaviorSimulator.random_delay(180, 650)
        page.wait_for_timeout(random.randint(350, 700))


def _split_text_segments(text: str) -> List[str]:
    """分割文本为小段"""
    if len(text) <= 8:
        return [text]
    segments = []
    idx = 0
    while idx < len(text):
        step = random.randint(2, 6)
        segments.append(text[idx : idx + step])
        idx += step
    return segments


def _split_text_natural(text: str) -> List[str]:
    """按自然语言分段（句子、短语）"""
    # 按标点符号分段
    import re
    # 匹配句子结束符号或换行
    pattern = r'([.!?\n:]+\s*)'
    parts = re.split(pattern, text)
    
    segments = []
    current = ""
    
    for part in parts:
        if not part:
            continue
        current += part
        # 如果遇到句子结束或长度超过 30，就作为一段
        if re.match(r'[.!?\n:]+\s*$', part) or len(current) > 30:
            if current.strip():
                segments.append(current)
            current = ""
    
    # 添加剩余部分
    if current.strip():
        segments.append(current)
    
    # 如果没有分段成功，按固定长度分
    if not segments:
        segments = [text[i:i+20] for i in range(0, len(text), 20)]
    
    return segments


def _activate_chrome_window() -> None:
    """激活 Chrome 窗口到前台"""
    try:
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to activate'],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        pass


def _pause_for_observation(label: str, step_pause_ms: int) -> None:
    """可观察停顿"""
    if step_pause_ms <= 0:
        return
    print(f"   👀 {label}，停顿 {step_pause_ms}ms")
    time.sleep(step_pause_ms / 1000)


def _save_debug_artifacts(page: Page) -> None:
    """保存调试信息"""
    try:
        Path("/tmp/xpost_debug.html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        print(f"   ⚠️  保存页面源码失败: {exc}")
    try:
        page.screenshot(path="/tmp/xpost_debug.png", full_page=True)
    except Exception as exc:
        print(f"   ⚠️  保存截图失败: {exc}")


def _find_editable_handle(page: Page, selectors: List[str]):
    """查找可编辑的输入框"""
    for selector in selectors:
        try:
            handles = page.query_selector_all(selector)
        except Exception:
            continue
        for handle in handles:
            try:
                state = handle.evaluate(
                    """
                    (el) => {
                      const style = window.getComputedStyle(el);
                      const rect = el.getBoundingClientRect();
                      const visible = style.display !== 'none' &&
                                      style.visibility !== 'hidden' &&
                                      style.opacity !== '0' &&
                                      rect.width > 0 &&
                                      rect.height > 0;
                      const editable = el.isContentEditable ||
                                       el.getAttribute('contenteditable') === 'true' ||
                                       el.getAttribute('role') === 'textbox';
                      const disabled = !!el.disabled ||
                                       (el.getAttribute('aria-disabled') || '').toLowerCase() === 'true' ||
                                       el.getAttribute('readonly') !== null;
                      const inDialog = !!el.closest('div[aria-modal="true"][role="dialog"], div[role="dialog"]');
                      return { visible, editable, disabled, inDialog };
                    }
                    """
                )
            except Exception:
                continue
            if state.get("visible") and state.get("editable") and not state.get("disabled"):
                return handle, selector, bool(state.get("inDialog"))
    return None, None, False


def input_post_text(page: Page, text: str, step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    """输入 Post 文本"""
    print("✍️  输入 Post 文本...")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"   🔄 尝试 {attempt + 1}/{max_retries}...")
            handle, matched_selector, in_dialog = _find_editable_handle(page, SELECTORS["textarea"])
            
            if handle is None:
                raise RuntimeError("未找到 Post 输入框")
            
            print(f"   ℹ️  使用输入框: {matched_selector}{' (dialog)' if in_dialog else ''}")
            
            # 聚焦并清空
            handle.evaluate(
                """
                (el) => {
                  el.scrollIntoView({block: 'center', inline: 'nearest'});
                  el.focus();
                  el.click();
                }
                """
            )
            _activate_chrome_window()
            HumanBehaviorSimulator.random_delay(250, 600)
            
            # 清空现有内容
            try:
                page.keyboard.press("Meta+A")
                page.keyboard.press("Backspace")
                page.wait_for_timeout(200)
            except Exception:
                pass
            
            # 分段输入文本，模拟真人打字
            print(f"   📝 模拟打字输入 ({len(text)} 字符)...")
            handle.evaluate("(el) => el.focus()")
            page.wait_for_timeout(300)
            
            # 将文本按句子或短语分段（更自然）
            segments = _split_text_natural(text)
            for i, segment in enumerate(segments):
                # 使用 type 方法逐字符输入，延迟 80-150ms
                page.keyboard.type(segment, delay=random.randint(80, 150))
                
                # 段落间随机停顿（模拟思考）
                if i < len(segments) - 1:
                    pause = random.randint(150, 400)
                    page.wait_for_timeout(pause)
            
            # 输入完成后等待
            page.wait_for_timeout(600)
            
            # 验证输入
            page.wait_for_timeout(400)
            current_text = handle.evaluate(
                "el => el.innerText || el.textContent || el.value || ''"
            ) or ""
            
            # 清理文本用于比较（移除多余空白）
            expected = text.strip()
            actual = current_text.strip()
            
            print(f"   🔍 验证: 期望 {len(expected)} 字符, 实际 {len(actual)} 字符")
            
            # 检查文本是否完整
            if expected in actual or actual in expected or len(actual) >= len(expected) * 0.95:
                print(f"   ✅ 文本输入成功 (验证: {len(actual)} 字符)")
                _pause_for_observation("文本已输入", step_pause_ms)
                return True
            
            # 如果验证失败，打印详细信息
            print(f"   ⚠️  文本验证失败:")
            print(f"       期望: {expected[:100]}...")
            print(f"       实际: {actual[:100]}...")
            
            raise RuntimeError(f"输入验证失败: 期望 {len(expected)} 字符, 实际 {len(actual)} 字符")
            
        except Exception as exc:
            print(f"   ⚠️  输入失败: {exc}")
            logging.error("输入文本失败（尝试 %s）: %s", attempt + 1, exc, exc_info=True)
            if attempt < max_retries - 1:
                print(f"   🔄 等待 2 秒后重试...")
                page.wait_for_timeout(2000)
    
    _save_debug_artifacts(page)
    raise RuntimeError("未找到文本框或无法输入文本")


def upload_post_media(page: Page, media: List[str], step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    """上传媒体附件"""
    if not media:
        return True
    
    print(f"   🖼️  上传 {len(media)} 个媒体附件...")
    
    # 查找文件上传控件
    matched_selector = None
    for selector in SELECTORS["file_input"]:
        try:
            if page.query_selector(selector):
                matched_selector = selector
                break
        except Exception:
            continue
    
    if matched_selector is None:
        _save_debug_artifacts(page)
        raise RuntimeError("未找到媒体上传 input")
    
    handle = page.query_selector(matched_selector)
    if handle is None:
        _save_debug_artifacts(page)
        raise RuntimeError(f"未找到媒体上传控件句柄: {matched_selector}")
    
    # 上传媒体
    abs_media = [str(Path(media_path).expanduser().resolve()) for media_path in media]
    handle.set_input_files(abs_media, timeout=10000)
    page.wait_for_timeout(2500)
    _activate_chrome_window()
    
    # 验证上传
    attached = page.eval_on_selector(
        matched_selector,
        "(el) => (el.files && el.files.length) || 0",
    ) or 0
    
    preview_count = page.evaluate(
        """
        () => {
          const selectors = [
            'button[data-testid="removeMedia"]',
            'button[aria-label*="Remove media"]',
            'div[data-testid="attachments"] img',
            'div[data-testid="attachments"] video',
            'img[src^="blob:"]',
            'video[src^="blob:"]'
          ];
          return Math.max(0, ...selectors.map((selector) => document.querySelectorAll(selector).length));
        }
        """
    )
    
    detected = max(attached, preview_count)
    if detected < len(media):
        _save_debug_artifacts(page)
        raise RuntimeError(f"媒体上传不完整：期望 {len(media)} 个，实际检测 {detected} 个")
    
    print(f"   ✅ 媒体上传成功 (检测到 {detected} 个)")
    _pause_for_observation("媒体已插入", step_pause_ms)
    return True


upload_post_images = upload_post_media


def click_post_button(page: Page, publish: bool = False, step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    """点击发布按钮"""
    action = "发布" if publish else "保存草稿"
    print(f"   🚀 {action}中...")
    
    if not publish:
        print("   ✅ 草稿模式完成（未自动点击发布）")
        return True
    
    ready_timeout_ms = int(os.environ.get("XPOST_POST_BUTTON_READY_TIMEOUT_MS", "90000"))
    poll_ms = int(os.environ.get("XPOST_POST_BUTTON_POLL_MS", "1500"))
    deadline = time.time() + (ready_timeout_ms / 1000)

    while True:
        for selector in SELECTORS["post_button"]:
            try:
                handle = page.query_selector(selector)
                if not handle:
                    continue
                
                disabled = handle.evaluate(
                    """
                    (el) => {
                      const ariaDisabled = (el.getAttribute('aria-disabled') || '').toLowerCase();
                      return ariaDisabled === 'true' || !!el.disabled;
                    }
                    """
                )
                
                if disabled:
                    print(f"   ⚠️  发布按钮未激活: {selector}")
                    continue
                
                _pause_for_observation("准备点击发布", step_pause_ms)
                
                try:
                    handle.evaluate(
                        """
                        (el) => {
                          el.scrollIntoView({block: 'center', inline: 'nearest'});
                          el.click();
                        }
                        """
                    )
                except Exception:
                    handle.click(timeout=5000, force=True)
                
                page.wait_for_timeout(2500)
                
                # 验证提交完成
                try:
                    page.wait_for_function(
                        """
                        () => {
                          const urlOk = !window.location.href.includes('/compose/post');
                          const composerGone = !document.querySelector('div[data-testid="tweetTextarea_0"], div[contenteditable="true"][role="textbox"]');
                          return urlOk || composerGone;
                        }
                        """,
                        timeout=12000,
                    )
                    print(f"   ✅ 找到并点击发布按钮: {selector}")
                    print("   ✅ 发布成功")
                    _pause_for_observation("发布已完成", step_pause_ms)
                    return True
                except Exception:
                    print(f"   ⚠️  已点击按钮但未确认提交完成: {selector}")
                    _pause_for_observation("按钮已点击，等待页面收尾", step_pause_ms)
                    return True
                    
            except PlaywrightTimeoutError:
                continue
            except Exception as exc:
                print(f"   ⚠️  点击发布按钮失败 {selector}: {exc}")
                continue

        if time.time() >= deadline:
            break

        print("   ⏳ 发布按钮仍在处理中，等待后重试...")
        page.wait_for_timeout(min(poll_ms, max(250, int((deadline - time.time()) * 1000))))
    
    _save_debug_artifacts(page)
    print("   ⚠️  未找到发布按钮")
    return False


def initialize_login_session(profile_dir: Path = PROFILE_DIR, timeout: int = 600) -> bool:
    """初始化登录会话"""
    session = None
    
    try:
        print("\n🌐 启动真实 Google Chrome...")
        session = create_session(profile_dir=profile_dir, headless=False)
        page = session.create_task_page()
        
        print(f"   ℹ️  使用持久化目录: {profile_dir}")
        
        # 检查登录状态
        if session.check_login_status(HOME_URL):
            print("✅ 检测到现有登录态，已可直接复用")
            return True
        
        # 需要登录
        print(f"\n📄 打开登录页: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        
        if not session.wait_for_login(timeout=timeout):
            raise RuntimeError("登录初始化超时或失败")
        
        # 验证登录成功
        page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        
        if not session.check_login_status(HOME_URL):
            raise RuntimeError("登录完成后仍未检测到有效会话")
        
        print("✅ 登录态已保存，后续 post 将直接复用")
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断登录初始化")
        return False
    except (RuntimeError, PlaywrightError) as exc:
        print(f"\n❌ 登录初始化失败: {exc}")
        logging.error("登录初始化失败: %s", exc, exc_info=True)
        return False
    finally:
        if session is not None:
            session.close()


def auto_publish_post(
    text: str,
    media: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
    publish: bool = False,
    wait_after: bool = True,
    step_pause_ms: int = STEP_PAUSE_MS,
) -> bool:
    """自动发布 Post"""
    print("[DEBUG] 进入 auto_publish_post 函数")
    session = None
    
    # 读取环境变量
    if os.environ.get("XPOST_NO_WAIT") == "1":
        wait_after = False
    
    try:
        print("🔍 验证输入参数...")
        print(f"[DEBUG] text={text[:50]}...")
        validate_text_length(text)
        media_paths = media if media is not None else images
        validate_media(media_paths)
        print("✅ 输入验证通过")
        
        print("\n🌐 启动真实 Google Chrome 并附着 CDP...")
        print(f"[DEBUG] PROFILE_DIR={PROFILE_DIR}")
        print("[DEBUG] 调用 create_session...")
        session = create_session(profile_dir=PROFILE_DIR, headless=False)
        print("[DEBUG] create_session 返回成功")
        page = session.create_task_page()
        _activate_chrome_window()
        
        print(f"   ℹ️  使用持久化目录: {PROFILE_DIR}")
        
        print("\n🔐 检查登录状态...")
        print(f"[DEBUG] 调用 check_login_status({HOME_URL})...")
        if not session.check_login_status(HOME_URL):
            raise RuntimeError(
                "未检测到已登录的 post 会话，请先运行 `python auto_publish_post.py --setup-login` "
                "或 `python xpost.py post-login` 完成一次手工登录"
            )
        print("✅ 已登录")
        
        print(f"\n📄 打开 Post 编辑器: {POST_URL}")
        print("[DEBUG] 调用 page.goto...")
        page.goto(POST_URL, wait_until="domcontentloaded", timeout=60000)
        print("[DEBUG] page.goto 返回成功")
        page.wait_for_timeout(2500)
        _activate_chrome_window()
        
        HumanBehaviorSimulator.warmup_page(page)
        
        if not input_post_text(page, text, step_pause_ms=step_pause_ms):
            raise RuntimeError("文本输入失败")
        
        if media_paths and not upload_post_media(page, media_paths, step_pause_ms=step_pause_ms):
            raise RuntimeError("媒体上传失败")
        
        if not click_post_button(page, publish, step_pause_ms=step_pause_ms):
            raise RuntimeError("发布按钮操作失败")
        
        if wait_after and not publish:
            print("\n⏸️  草稿已准备好，按 Enter 继续...")
            input()
        
        print("\n✅ 操作完成")
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        return False
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"\n❌ 操作失败: {exc}")
        logging.error("Post 发布失败: %s", exc, exc_info=True)
        return False
    except PlaywrightError as exc:
        print(f"\n❌ 浏览器自动化失败: {exc}")
        logging.error("Patchright 自动化失败: %s", exc, exc_info=True)
        return False
    except Exception as exc:
        print(f"\n❌ 未知错误: {exc}")
        logging.error("未知错误: %s", exc, exc_info=True)
        return False
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    print("[DEBUG] 脚本启动")
    print(f"[DEBUG] sys.argv = {sys.argv}")
    parser = argparse.ArgumentParser(description="X Post 自动发布工具")
    parser.add_argument("text", nargs="?", help="Post 文本内容")
    parser.add_argument("--media", nargs="+", help="媒体路径（图片或视频，最多 4 个）")
    parser.add_argument("--images", nargs="+", help="图片路径（兼容旧参数）")
    parser.add_argument("--publish", action="store_true", help="直接发布")
    parser.add_argument("--no-wait", action="store_true", help="完成后不等待")
    parser.add_argument("--observe-ms", type=int, default=STEP_PAUSE_MS, help="每个关键步骤后的可观察停顿毫秒数")
    parser.add_argument("--setup-login", action="store_true", help="仅初始化登录会话并保存持久化状态")
    parser.add_argument("--login-timeout", type=int, default=600, help="手工登录等待超时秒数")
    print("[DEBUG] 开始解析参数")
    args = parser.parse_args()
    print(f"[DEBUG] 参数解析完成: args={args}")
    
    if args.setup_login:
        print("[DEBUG] 执行 setup-login")
        success = initialize_login_session(timeout=args.login_timeout)
    else:
        if not args.text:
            parser.error("text 是必填参数，除非使用 --setup-login")
        print(f"[DEBUG] 调用 auto_publish_post, text={args.text}")
        media_paths = args.media or args.images
        success = auto_publish_post(
            text=args.text,
            media=media_paths,
            images=args.images if not args.media else None,
            publish=args.publish,
            wait_after=not args.no_wait,
            step_pause_ms=args.observe_ms,
        )
    
    print(f"[DEBUG] 执行完成, success={success}")
    sys.exit(0 if success else 1)
