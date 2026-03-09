#!/usr/bin/env python3
"""
X Post 自动发布系统（macOS）
使用真实 Google Chrome profile + Patchright CDP 附着，避免 chromedriver 版本耦合。
"""

import argparse
import logging
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
    from patchright.sync_api import Browser, BrowserContext, Locator, Page, Playwright, sync_playwright
except Exception:
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Browser = object
    BrowserContext = object
    Locator = object
    Page = object
    Playwright = object
    sync_playwright = None


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
MAX_TEXT_LENGTH = 280
MAX_IMAGES = 4
CHROME_BINARY = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
REMOTE_DEBUGGING_PORT = int(os.environ.get("XPOST_REMOTE_DEBUGGING_PORT", "19222"))
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
    "login_indicators": [
        'a[href="/login"]',
        'a[href*="flow/login"]',
        'input[autocomplete="username"]',
        'input[name="text"]',
        'input[autocomplete="current-password"]',
    ],
}


def validate_text_length(text: str) -> bool:
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"文本超过 {MAX_TEXT_LENGTH} 字符限制（当前：{len(text)}）")
    if not text.strip():
        raise ValueError("文本内容不能为空")
    return True


def validate_images(images: Optional[List[str]]) -> bool:
    if not images:
        return True
    if len(images) > MAX_IMAGES:
        raise ValueError(f"图片数量超过 {MAX_IMAGES} 张限制（当前：{len(images)}）")
    for img_path in images:
        if not Path(img_path).exists():
            raise FileNotFoundError(f"图片文件不存在: {img_path}")
    return True


class HumanBehaviorSimulator:
    @staticmethod
    def random_delay(min_ms: int = 500, max_ms: int = 2000) -> None:
        time.sleep(random.uniform(min_ms, max_ms) / 1000)

    @staticmethod
    def warmup_page(page: Page) -> None:
        print("   🔥 页面预热中...")
        # 对真实 Chrome 的 CDP 新建页，滚动/鼠标预热会偶发导致 page target 关闭。
        # 这里保留轻量停顿，优先稳定性。
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


def _ensure_patchright_available() -> None:
    if sync_playwright is None:
        raise RuntimeError(
            "patchright 未安装。请先在当前 .venv 中安装 patchright，并执行 `python -m patchright install chromium`。"
        )
    if not CHROME_BINARY.exists():
        raise RuntimeError(f"未找到 Google Chrome: {CHROME_BINARY}")

 
def _pid_file_path(profile_dir: Path) -> Path:
    return profile_dir / ".xpost_chrome.pid"


def _cleanup_profile_locks(profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("Singleton*", "LockFile", "RunningChromeVersion"):
        for path in profile_dir.glob(pattern):
            try:
                if path.is_file() or path.is_symlink():
                    path.unlink(missing_ok=True)
            except OSError:
                continue


def _is_process_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid(profile_dir: Path) -> Optional[int]:
    pid_file = _pid_file_path(profile_dir)
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_pid(profile_dir: Path, pid: int) -> None:
    try:
        _pid_file_path(profile_dir).write_text(str(pid), encoding="utf-8")
    except OSError:
        pass


def _clear_pid(profile_dir: Path) -> None:
    try:
        _pid_file_path(profile_dir).unlink(missing_ok=True)
    except OSError:
        pass


def _profile_process_pids(profile_dir: Path) -> List[int]:
    try:
        result = subprocess.run(
            ["pgrep", "-af", "--", f"--user-data-dir={profile_dir}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return []

    pids = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if not parts:
            continue
        try:
            pids.append(int(parts[0]))
        except ValueError:
            continue
    return pids


def _cdp_endpoint_url(port: int = REMOTE_DEBUGGING_PORT) -> str:
    return f"http://127.0.0.1:{port}"


def _cdp_is_ready(port: int = REMOTE_DEBUGGING_PORT) -> bool:
    try:
        with urllib.request.urlopen(f"{_cdp_endpoint_url(port)}/json/version", timeout=1) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _wait_for_cdp(port: int = REMOTE_DEBUGGING_PORT, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _cdp_is_ready(port):
            return True
        time.sleep(1)
    return False


def _profile_in_use_without_cdp(profile_dir: Path, port: int = REMOTE_DEBUGGING_PORT) -> bool:
    pid = _read_pid(profile_dir)
    if pid and _is_process_alive(pid):
        return not _cdp_is_ready(port)
    if _profile_process_pids(profile_dir):
        return not _cdp_is_ready(port)
    return False


def _launch_real_chrome(profile_dir: Path, start_url: str, port: int = REMOTE_DEBUGGING_PORT) -> Tuple[int, bool]:
    _ensure_patchright_available()
    profile_dir.mkdir(parents=True, exist_ok=True)

    existing_pid = _read_pid(profile_dir)
    if existing_pid and _is_process_alive(existing_pid) and _cdp_is_ready(port):
        return existing_pid, False
    existing_profile_pids = _profile_process_pids(profile_dir)
    if _cdp_is_ready(port):
        if existing_profile_pids:
            _write_pid(profile_dir, existing_profile_pids[0])
            return existing_profile_pids[0], False
        raise RuntimeError(f"CDP 端口 {port} 已被其他进程占用，请更换端口或先关闭占用进程")

    if _profile_in_use_without_cdp(profile_dir, port):
        raise RuntimeError(
            f"检测到 profile 正被另一个 Chrome 实例占用但未开启 CDP，请先关闭该实例后重试: {profile_dir}"
        )

    _cleanup_profile_locks(profile_dir)
    proc = subprocess.Popen(
        [
            str(CHROME_BINARY),
            f"--user-data-dir={profile_dir}",
            "--profile-directory=Default",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-notifications",
            "--start-maximized",
            start_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_for_cdp(port):
        raise RuntimeError(f"真实 Chrome CDP 未在端口 {port} 上就绪")
    _write_pid(profile_dir, proc.pid)
    return proc.pid, True


def _connect_browser(port: int = REMOTE_DEBUGGING_PORT) -> tuple[Playwright, Browser, BrowserContext, Page]:
    _ensure_patchright_available()
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(_cdp_endpoint_url(port), timeout=30000, is_local=True)
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    return playwright, browser, context, page


def _activate_chrome_window() -> None:
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Google Chrome" to activate',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        pass


def _pause_for_observation(label: str, step_pause_ms: int) -> None:
    if step_pause_ms <= 0:
        return
    print(f"   👀 {label}，停顿 {step_pause_ms}ms")
    time.sleep(step_pause_ms / 1000)


def _save_debug_artifacts(page: Page) -> None:
    try:
        Path("/tmp/xpost_debug.html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        print(f"   ⚠️  保存页面源码失败: {exc}")
    try:
        page.screenshot(path="/tmp/xpost_debug.png", full_page=True)
    except Exception as exc:
        print(f"   ⚠️  保存截图失败: {exc}")


def _split_text_segments(text: str) -> List[str]:
    if len(text) <= 8:
        return [text]
    segments = []
    idx = 0
    while idx < len(text):
        step = random.randint(2, 6)
        segments.append(text[idx : idx + step])
        idx += step
    return segments


def _first_visible_locator(page: Page, selectors: List[str], timeout_ms: int = 4000) -> Optional[Locator]:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return None


def _query_visible_selector(page: Page, selectors: List[str]) -> Optional[str]:
    for selector in selectors:
        try:
            handle = page.query_selector(selector)
            if not handle:
                continue
            visible = handle.evaluate(
                """
                (el) => {
                  const style = window.getComputedStyle(el);
                  const rect = el.getBoundingClientRect();
                  return style.display !== 'none' &&
                         style.visibility !== 'hidden' &&
                         style.opacity !== '0' &&
                         rect.width > 0 &&
                         rect.height > 0;
                }
                """
            )
            if visible:
                return selector
        except Exception:
            continue
    return None


def _find_editable_handle(page: Page, selectors: List[str]):
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


def _query_existing_selector(page: Page, selectors: List[str]) -> Optional[str]:
    for selector in selectors:
        try:
            if page.query_selector(selector):
                return selector
        except Exception:
            continue
    return None


def _read_editor_text(locator: Locator) -> str:
    try:
        return locator.evaluate("el => el.innerText || el.textContent || el.value || ''") or ""
    except Exception:
        return ""


def check_login_status(page: Page) -> bool:
    current_url = page.url or ""
    if "login" in current_url.lower() or "flow/login" in current_url.lower():
        return False
    for selector in SELECTORS["login_indicators"]:
        try:
            if page.locator(selector).first.is_visible():
                return False
        except Exception:
            continue
    return True


def wait_for_login(page: Page, timeout: int = 300) -> bool:
    print()
    print("⚠️  检测到未登录状态！")
    print("=" * 60)
    print("📢 请在当前打开的 Google Chrome 专用 profile 中完成 X 登录")
    print("   1. 输入 X 用户名/邮箱")
    print("   2. 输入密码")
    print("   3. 完成所有安全验证")
    print("   4. 登录成功后脚本会自动继续")
    print("=" * 60)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_login_status(page):
            print("✅ 登录成功！")
            return True
        time.sleep(3)
    print("❌ 登录超时")
    return False


def initialize_login_session(profile_dir: Path = PROFILE_DIR, timeout: int = 600) -> bool:
    playwright = None

    try:
        print("\n🌐 启动真实 Google Chrome...")
        _pid, launched = _launch_real_chrome(profile_dir, HOME_URL)
        playwright, _browser, _context, page = _connect_browser()
        print(f"   ℹ️  使用持久化目录: {profile_dir}")
        if launched:
            print(f"   ℹ️  已为该 profile 启动独立 Chrome，CDP 端口: {REMOTE_DEBUGGING_PORT}")
        else:
            print("   ℹ️  复用已运行的专用 Chrome 实例")

        page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        if check_login_status(page):
            print("✅ 检测到现有登录态，已可直接复用")
            return True

        print(f"\n📄 打开登录页: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        if not wait_for_login(page, timeout=timeout):
            raise RuntimeError("登录初始化超时或失败")

        page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        if not check_login_status(page):
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
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass


def _open_post_page(page: Page) -> None:
    page.goto(POST_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    _activate_chrome_window()
    if POST_URL not in (page.url or ""):
        print(f"   ⚠️  当前页面不是目标页，重新导航: {page.url}")
        page.goto(POST_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        _activate_chrome_window()


def _find_textarea_handle(page: Page):
    handle, selector, in_dialog = _find_editable_handle(page, SELECTORS["textarea"])
    if handle is not None:
        return handle, selector, in_dialog
    return None, None, False


def input_post_text(page: Page, text: str, step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    print("✍️  输入 Post 文本...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   🔄 尝试 {attempt + 1}/{max_retries}...")
            handle, matched_selector, in_dialog = _find_textarea_handle(page)
            if handle is None:
                raise RuntimeError("未找到 Post 输入框")
            print(
                "   ℹ️  使用输入框候选: "
                f"{matched_selector}"
                f"{' (dialog)' if in_dialog else ''}"
            )

            handle.evaluate(
                """
                (el) => {
                  el.scrollIntoView({block: 'center', inline: 'nearest'});
                  el.focus();
                  el.click();
                }
                """,
            )
            _activate_chrome_window()
            HumanBehaviorSimulator.random_delay(250, 600)

            try:
                page.keyboard.press("Meta+A")
                page.keyboard.press("Backspace")
            except Exception:
                pass

            try:
                for segment in _split_text_segments(text):
                    page.keyboard.insert_text(segment)
                    HumanBehaviorSimulator.random_delay(35, 95)
            except Exception as exc:
                print(f"   ⚠️  模拟输入失败，切换原生输入: {exc}")
                handle.evaluate("(el) => el.focus()")
                page.keyboard.insert_text(text)
                page.wait_for_timeout(500)

            current_text = handle.evaluate(
                "el => el.innerText || el.textContent || el.value || ''",
            ) or ""
            if not current_text.strip():
                current_text = handle.evaluate(
                    """
                    (el, value) => {
                      el.focus();
                      const contents = el.querySelector('[data-contents="true"]');
                      if (contents) {
                        contents.innerHTML = '';
                        const block = document.createElement('div');
                        block.setAttribute('data-block', 'true');
                        block.setAttribute('data-editor', 'xpost');
                        block.setAttribute('data-offset-key', 'xpost-0-0');
                        const inner = document.createElement('div');
                        inner.className = 'public-DraftStyleDefault-block public-DraftStyleDefault-ltr';
                        inner.setAttribute('data-offset-key', 'xpost-0-0');
                        const span = document.createElement('span');
                        span.setAttribute('data-offset-key', 'xpost-0-0');
                        span.appendChild(document.createTextNode(value));
                        inner.appendChild(span);
                        block.appendChild(inner);
                        contents.appendChild(block);
                      } else {
                        el.textContent = value;
                      }
                      el.dispatchEvent(new InputEvent('beforeinput', {
                        bubbles: true,
                        cancelable: true,
                        data: value,
                        inputType: 'insertText'
                      }));
                      el.dispatchEvent(new InputEvent('input', {
                        bubbles: true,
                        data: value,
                        inputType: 'insertText'
                      }));
                      el.dispatchEvent(new Event('change', { bubbles: true }));
                      return el.innerText || el.textContent || el.value || '';
                    }
                    """,
                    text,
                ) or ""

            if text.strip() and text.strip() in current_text:
                print(f"   ✅ 文本输入成功 (验证: {len(current_text)} 字符)")
                _pause_for_observation("文本已输入", step_pause_ms)
                return True
            if current_text.strip():
                print(f"   ✅ 文本输入完成 (检测到 {len(current_text)} 字符)")
                _pause_for_observation("文本已进入编辑器", step_pause_ms)
                return True
            raise RuntimeError("输入后文本框仍为空")
        except Exception as exc:
            print(f"   ⚠️  输入失败: {exc}")
            logging.error("输入文本失败（尝试 %s）: %s", attempt + 1, exc, exc_info=True)
            if attempt < max_retries - 1:
                page.wait_for_timeout(2000)
    _save_debug_artifacts(page)
    raise RuntimeError("未找到文本框或无法输入文本")


def _count_uploaded_media(page: Page) -> int:
    try:
        return page.evaluate(
            """
            () => {
              const selectors = [
                'button[data-testid="removeMedia"]',
                'button[aria-label*="Remove media"]',
                'div[data-testid="attachments"] img',
                'img[src^="blob:"]'
              ];
              return Math.max(0, ...selectors.map((selector) => document.querySelectorAll(selector).length));
            }
            """
        )
    except Exception:
        return 0


def upload_post_images(page: Page, images: List[str], step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    if not images:
        return True

    print(f"   🖼️  上传 {len(images)} 张图片...")
    matched_selector = _query_existing_selector(page, SELECTORS["file_input"])
    if matched_selector is None:
        _save_debug_artifacts(page)
        raise RuntimeError("未找到图片上传 input")
    handle = page.query_selector(matched_selector)
    if handle is None:
        _save_debug_artifacts(page)
        raise RuntimeError(f"未找到图片上传控件句柄: {matched_selector}")

    abs_images = [str(Path(img_path).expanduser().resolve()) for img_path in images]
    handle.set_input_files(abs_images, timeout=10000)
    page.wait_for_timeout(2500)
    _activate_chrome_window()

    attached = page.eval_on_selector(
        matched_selector,
        "(el) => (el.files && el.files.length) || 0",
    ) or 0
    preview_count = _count_uploaded_media(page)
    detected = max(attached, preview_count)
    if detected < len(images):
        _save_debug_artifacts(page)
        raise RuntimeError(f"图片上传不完整：期望 {len(images)} 张，实际检测 {detected} 张")

    print(f"   ✅ 图片上传成功 (检测到 {detected} 张)")
    _pause_for_observation("图片已插入", step_pause_ms)
    return True


def _post_submission_completed(page: Page) -> bool:
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
        return True
    except Exception:
        return False


def click_post_button(page: Page, publish: bool = False, step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    action = "发布" if publish else "保存草稿"
    print(f"   🚀 {action}中...")

    if not publish:
        print("   ✅ 草稿模式完成（未自动点击发布）")
        return True

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

            if _post_submission_completed(page):
                print(f"   ✅ 找到并点击发布按钮: {selector}")
                print("   ✅ 发布成功")
                _pause_for_observation("发布已完成", step_pause_ms)
                return True

            print(f"   ⚠️  已点击按钮但未确认提交完成: {selector}")
            _pause_for_observation("按钮已点击，等待页面收尾", step_pause_ms)
            return True
        except PlaywrightTimeoutError:
            continue
        except Exception as exc:
            print(f"   ⚠️  点击发布按钮失败 {selector}: {exc}")
            continue

    try:
        button_state = page.evaluate(
            """
            () => {
              const btn = document.querySelector(
                'button[data-testid="tweetButton"],button[data-testid="tweetButtonInline"],[data-testid="tweetButton"],[data-testid="tweetButtonInline"]'
              );
              if (!btn) return { found: false };
              return {
                found: true,
                text: (btn.innerText || btn.textContent || '').trim(),
                ariaDisabled: btn.getAttribute('aria-disabled'),
                disabled: !!btn.disabled
              };
            }
            """
        )
        print(f"   ℹ️  按钮状态: {button_state}")
    except Exception as exc:
        print(f"   ⚠️  读取按钮状态失败: {exc}")

    _save_debug_artifacts(page)
    print("   ⚠️  未找到发布按钮")
    return False


def auto_publish_post(
    text: str,
    images: Optional[List[str]] = None,
    publish: bool = False,
    wait_after: bool = True,
    step_pause_ms: int = STEP_PAUSE_MS,
) -> bool:
    playwright = None

    if os.environ.get("XPOST_NO_WAIT") == "1":
        wait_after = False

    try:
        print("🔍 验证输入参数...")
        validate_text_length(text)
        validate_images(images)
        print("✅ 输入验证通过")

        print("\n🌐 启动真实 Google Chrome 并附着 CDP...")
        _launch_real_chrome(PROFILE_DIR, HOME_URL)
        playwright, _browser, _context, page = _connect_browser()
        _activate_chrome_window()
        print(f"   ℹ️  使用持久化目录: {PROFILE_DIR}")
        print(f"   ℹ️  CDP 端口: {REMOTE_DEBUGGING_PORT}")

        print(f"\n📄 打开 Post 编辑器: {POST_URL}")
        _open_post_page(page)

        print("\n🔐 检查登录状态...")
        if not check_login_status(page):
            raise RuntimeError(
                "未检测到已登录的 post 会话，请先运行 `python auto_publish_post.py --setup-login` "
                "或 `python xpost.py post-login` 完成一次手工登录"
            )
        print("✅ 已登录")

        HumanBehaviorSimulator.warmup_page(page)

        if not input_post_text(page, text, step_pause_ms=step_pause_ms):
            raise RuntimeError("文本输入失败")

        if images and not upload_post_images(page, images, step_pause_ms=step_pause_ms):
            raise RuntimeError("图片上传失败")

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
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X Post 自动发布工具")
    parser.add_argument("text", nargs="?", help="Post 文本内容")
    parser.add_argument("--images", nargs="+", help="图片路径（最多 4 张）")
    parser.add_argument("--publish", action="store_true", help="直接发布")
    parser.add_argument("--no-wait", action="store_true", help="完成后不等待")
    parser.add_argument("--observe-ms", type=int, default=STEP_PAUSE_MS, help="每个关键步骤后的可观察停顿毫秒数")
    parser.add_argument("--setup-login", action="store_true", help="仅初始化登录会话并保存持久化状态")
    parser.add_argument("--login-timeout", type=int, default=600, help="手工登录等待超时秒数")
    args = parser.parse_args()

    if args.setup_login:
        success = initialize_login_session(timeout=args.login_timeout)
    else:
        if not args.text:
            parser.error("text 是必填参数，除非使用 --setup-login")
        success = auto_publish_post(
            text=args.text,
            images=args.images,
            publish=args.publish,
            wait_after=not args.no_wait,
            step_pause_ms=args.observe_ms,
        )
    sys.exit(0 if success else 1)
