#!/usr/bin/env python3
"""
X Reply 自动回复系统（macOS）
复用 browser_cdp_session.py 共享浏览器会话层 + auto_publish_post.py 人类行为模拟

子命令：
  extract  — 打开推文详情页，提取主帖正文/作者/语言
  send     — 打开推文详情页，点击 Reply，逐字输入回复内容，点击发送
"""

import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional

from browser_cdp_session import ChromeCDPSession, create_session

try:
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
    from patchright.sync_api import Page
except Exception:
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Page = object

logging.basicConfig(
    filename="xpost_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = Path(os.environ.get("XPOST_PROFILE_DIR") or (BASE_DIR / "chrome_data_mirror"))
HOME_URL = "https://x.com/home"
MAX_REPLY_LENGTH = 280
STEP_PAUSE_MS = int(os.environ.get("XPOST_STEP_PAUSE_MS", "900"))

REPLY_SELECTORS = {
    "reply_button": [
        '[data-testid="reply"]',
        'button[aria-label*="Reply"]',
        'div[role="button"][aria-label*="Reply"]',
    ],
    "reply_composer": [
        'div[data-testid="tweetTextarea_0"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"]',
    ],
    "send_reply_button": [
        'button[data-testid="tweetButton"]',
        'button[data-testid="tweetButtonInline"]',
        '[data-testid="tweetButton"]',
        '[data-testid="tweetButtonInline"]',
    ],
}


def _clean_tweet_url(url: str) -> str:
    """去掉 URL 中的锚点和查询参数，保留干净的 tweet URL"""
    url = url.split("#")[0].split("?")[0].rstrip("/")
    match = re.search(r"(https?://(?:x|twitter)\.com/\w+/status/\d+)", url)
    if not match:
        raise ValueError(f"无效的推文 URL: {url}")
    return match.group(1)


def _random_delay(min_ms: int = 300, max_ms: int = 800) -> None:
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def _activate_chrome_window() -> None:
    try:
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to activate'],
            capture_output=True, text=True, timeout=5,
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
        Path("/tmp/xpost_reply_debug.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass
    try:
        page.screenshot(path="/tmp/xpost_reply_debug.png", full_page=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 提取推文正文
# ---------------------------------------------------------------------------

_EXTRACT_JS = """
() => {
  const statusMatch = window.location.pathname.match(/\\/status\\/(\\d+)/);
  const statusPath = statusMatch ? '/status/' + statusMatch[1] : '';

  const articles = Array.from(document.querySelectorAll('article[data-testid="tweet"]'));
  if (!articles.length) return JSON.stringify({ error: 'NO_ARTICLE' });

  let mainArticle = articles[0];
  if (statusPath) {
    for (const a of articles) {
      const link = a.querySelector('a[href*="/status/"]');
      if (link && (link.getAttribute('href') || '').includes(statusPath)) {
        mainArticle = a;
        break;
      }
    }
  }

  const textEl = mainArticle.querySelector('[data-testid="tweetText"]');
  const text = textEl ? textEl.innerText.trim() : '';
  const nameEl = mainArticle.querySelector('[data-testid="User-Name"]');
  const handle = nameEl ? nameEl.innerText.trim() : '';
  const lang = textEl ? (textEl.getAttribute('lang') || 'unknown') : 'unknown';

  if (!text) return JSON.stringify({ error: 'NO_TEXT', handle });
  return JSON.stringify({ handle, text, lang });
}
"""


def extract_tweet(page: Page, url: str, step_pause_ms: int = STEP_PAUSE_MS) -> dict:
    """打开推文页面并提取主帖正文"""
    clean_url = _clean_tweet_url(url)
    print(f"📄 打开推文: {clean_url}")
    page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    _activate_chrome_window()

    for attempt in range(2):
        raw = page.evaluate(_EXTRACT_JS)
        data = json.loads(raw) if isinstance(raw, str) else raw
        if data.get("error") == "NO_ARTICLE":
            if attempt == 0:
                print("   ⏳ 页面未完全加载，等待 2 秒重试...")
                page.wait_for_timeout(2000)
                continue
            _save_debug_artifacts(page)
            raise RuntimeError("无法提取推文正文：页面未找到 article 元素")
        if data.get("error") == "NO_TEXT":
            _save_debug_artifacts(page)
            raise RuntimeError(f"推文正文为空（作者: {data.get('handle', '?')}）")
        if data.get("error"):
            raise RuntimeError(f"提取失败: {data['error']}")
        print(f"   ✅ 提取成功: @{data.get('handle', '?')} / {data.get('lang', '?')} / {len(data.get('text', ''))} 字符")
        _pause_for_observation("正文已提取", step_pause_ms)
        return data

    raise RuntimeError("提取推文正文失败")


# ---------------------------------------------------------------------------
# 查找主帖内的 Reply 按钮并点击
# ---------------------------------------------------------------------------

def _find_main_article_reply_button(page: Page):
    """在主帖 article 内查找 Reply 按钮句柄"""
    return page.evaluate("""
    () => {
      const statusMatch = window.location.pathname.match(/\\/status\\/(\\d+)/);
      const statusPath = statusMatch ? '/status/' + statusMatch[1] : '';

      const articles = Array.from(document.querySelectorAll('article[data-testid="tweet"]'));
      if (!articles.length) return { found: false, error: 'NO_ARTICLE' };

      let mainArticle = articles[0];
      if (statusPath) {
        for (const a of articles) {
          const link = a.querySelector('a[href*="/status/"]');
          if (link && (link.getAttribute('href') || '').includes(statusPath)) {
            mainArticle = a;
            break;
          }
        }
      }

      const btn = mainArticle.querySelector('[data-testid="reply"]');
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        return { found: true, testId: 'reply' };
      }

      const group = mainArticle.querySelector('[role="group"]');
      if (group) {
        const first = group.querySelector('button, div[role="button"]');
        if (first) {
          first.scrollIntoView({ block: 'center' });
          return { found: true, testId: 'group_first' };
        }
      }

      return { found: false, error: 'REPLY_BUTTON_NOT_FOUND' };
    }
    """)


def _click_reply_and_wait_composer(page: Page, timeout_ms: int = 12000) -> bool:
    """点击主帖 Reply 按钮，等待 composer 出现"""
    info = _find_main_article_reply_button(page)
    if not info.get("found"):
        raise RuntimeError(f"未找到 Reply 按钮: {info.get('error', '?')}")

    if info.get("testId") == "reply":
        handle = page.query_selector('[data-testid="reply"]')
    else:
        group = page.query_selector('article[data-testid="tweet"] [role="group"]')
        handle = group.query_selector("button, div[role=\"button\"]") if group else None

    if not handle:
        raise RuntimeError("Reply 按钮句柄获取失败")

    print("   🖱️  点击 Reply 按钮...")
    _random_delay(500, 1200)
    handle.evaluate("""
    (el) => {
      el.scrollIntoView({ block: 'center', inline: 'nearest' });
      el.focus();
      el.click();
    }
    """)
    _random_delay(300, 700)

    print(f"   ⏳ 等待 reply composer 出现 (最多 {timeout_ms // 1000}s)...")
    started = time.time()
    while (time.time() - started) * 1000 < timeout_ms:
        for selector in REPLY_SELECTORS["reply_composer"]:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    state = el.evaluate("""
                    (el) => ({
                      editable: el.isContentEditable || el.getAttribute('contenteditable') === 'true',
                      role: el.getAttribute('role'),
                      placeholder: el.getAttribute('data-placeholder') || el.getAttribute('aria-label') || '',
                    })
                    """)
                    if state.get("editable"):
                        print(f"   ✅ Composer 已就绪: {selector}")
                        _random_delay(800, 1500)
                        try:
                            el.focus()
                            el.click()
                        except Exception:
                            pass
                        _random_delay(400, 800)
                        return True
            except Exception:
                continue
        page.wait_for_timeout(200)

    _save_debug_artifacts(page)
    raise RuntimeError("Reply composer 未在超时时间内出现")


# ---------------------------------------------------------------------------
# 逐字输入回复内容（复用 auto_publish_post 的人类模拟策略）
# ---------------------------------------------------------------------------

def _split_text_segments(text: str):
    if len(text) <= 4:
        return [text]
    segments = []
    idx = 0
    while idx < len(text):
        step = random.randint(1, 4)
        segments.append(text[idx: idx + step])
        idx += step
    return segments


def _find_reply_editable(page: Page):
    """查找当前可见的 reply 输入框句柄"""
    for selector in REPLY_SELECTORS["reply_composer"]:
        try:
            handles = page.query_selector_all(selector)
        except Exception:
            continue
        for h in handles:
            try:
                state = h.evaluate("""
                (el) => {
                  const style = window.getComputedStyle(el);
                  const rect = el.getBoundingClientRect();
                  const visible = style.display !== 'none' &&
                                  style.visibility !== 'hidden' &&
                                  style.opacity !== '0' &&
                                  rect.width > 0 && rect.height > 0;
                  const editable = el.isContentEditable ||
                                   el.getAttribute('contenteditable') === 'true';
                  const inDialog = !!el.closest('div[role="dialog"]');
                  return { visible, editable, inDialog };
                }
                """)
            except Exception:
                continue
            if state.get("visible") and state.get("editable"):
                return h, selector, bool(state.get("inDialog"))
    return None, None, False


def input_reply_text(page: Page, text: str, step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    """逐字输入回复文本（模拟人类打字）"""
    print("✍️  输入回复文本...")
    max_retries = 3

    for attempt in range(max_retries):
        try:
            print(f"   🔄 尝试 {attempt + 1}/{max_retries}...")
            handle, matched_selector, in_dialog = _find_reply_editable(page)

            if handle is None:
                raise RuntimeError("未找到 reply 输入框")

            print(f"   ℹ️  使用输入框: {matched_selector}{' (dialog)' if in_dialog else ''}")

            handle.evaluate("""
            (el) => {
              el.scrollIntoView({ block: 'center', inline: 'nearest' });
              el.focus();
              el.click();
            }
            """)
            _activate_chrome_window()
            _random_delay(600, 1200)

            try:
                page.keyboard.press("Meta+A")
                _random_delay(100, 250)
                page.keyboard.press("Backspace")
            except Exception:
                pass

            _random_delay(400, 800)

            for i, segment in enumerate(_split_text_segments(text)):
                page.keyboard.type(segment, delay=random.randint(55, 140))
                if random.random() < 0.25:
                    _random_delay(300, 900)
                elif random.random() < 0.08:
                    _random_delay(800, 1800)

            page.wait_for_timeout(random.randint(600, 1200))

            current_text = handle.evaluate(
                "el => (el.innerText || el.textContent || '').replace(/\\u200b/g, '').trim()"
            ) or ""

            if text.strip() and text.strip() in current_text:
                print(f"   ✅ 文本输入成功 (验证: {len(current_text)} 字符)")
                _pause_for_observation("回复文本已输入", step_pause_ms)
                return True

            if current_text.strip():
                print(f"   ✅ 文本输入完成 (检测到 {len(current_text)} 字符)")
                _pause_for_observation("文本已进入编辑器", step_pause_ms)
                return True

            raise RuntimeError("输入后文本框仍为空")

        except Exception as exc:
            print(f"   ⚠️  输入失败: {exc}")
            logging.error("回复文本输入失败（尝试 %s）: %s", attempt + 1, exc, exc_info=True)
            if attempt < max_retries - 1:
                page.wait_for_timeout(2000)

    _save_debug_artifacts(page)
    raise RuntimeError("未找到回复输入框或无法输入文本")


# ---------------------------------------------------------------------------
# 点击 Reply 发送按钮
# ---------------------------------------------------------------------------

def click_reply_send(page: Page, step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    """查找并点击 Reply 发送按钮"""
    print("   🚀 发送回复...")

    for selector in REPLY_SELECTORS["send_reply_button"]:
        try:
            handle = page.query_selector(selector)
            if not handle:
                continue

            disabled = handle.evaluate("""
            (el) => {
              const ariaDisabled = (el.getAttribute('aria-disabled') || '').toLowerCase();
              return ariaDisabled === 'true' || !!el.disabled;
            }
            """)

            if disabled:
                print(f"   ⚠️  发送按钮未激活: {selector}")
                continue

            _pause_for_observation("准备点击发送", step_pause_ms)

            try:
                handle.evaluate("""
                (el) => {
                  el.scrollIntoView({ block: 'center', inline: 'nearest' });
                  el.click();
                }
                """)
            except Exception:
                handle.click(timeout=5000, force=True)

            page.wait_for_timeout(2500)

            try:
                page.wait_for_function("""
                () => {
                  const composerGone = !document.querySelector(
                    'div[data-testid="tweetTextarea_0"], div[contenteditable="true"][role="textbox"]'
                  );
                  const dialogGone = !document.querySelector('div[role="dialog"]');
                  return composerGone || dialogGone;
                }
                """, timeout=10000)
                print("   ✅ 回复发送成功")
                _pause_for_observation("回复已发送", step_pause_ms)
                return True
            except Exception:
                print("   ⚠️  已点击发送但未确认 composer 关闭，视为成功")
                _pause_for_observation("发送按钮已点击", step_pause_ms)
                return True

        except PlaywrightTimeoutError:
            continue
        except Exception as exc:
            print(f"   ⚠️  点击发送按钮失败 {selector}: {exc}")
            continue

    _save_debug_artifacts(page)
    print("   ❌ 未找到可用的发送按钮")
    return False


# ---------------------------------------------------------------------------
# 高层 API
# ---------------------------------------------------------------------------

def auto_extract_tweet(url: str, step_pause_ms: int = STEP_PAUSE_MS) -> dict:
    """提取推文正文（完整流程：启动浏览器 → 提取 → 关闭）"""
    session = None
    try:
        session = create_session(profile_dir=PROFILE_DIR, headless=False)
        page = session.create_task_page()
        _activate_chrome_window()

        if not session.check_login_status(HOME_URL):
            raise RuntimeError("未检测到已登录会话，请先运行 xpost post-login")

        return extract_tweet(page, url, step_pause_ms=step_pause_ms)

    finally:
        if session:
            session.close()


def auto_reply_post(
    url: str,
    text: str,
    publish: bool = False,
    step_pause_ms: int = STEP_PAUSE_MS,
) -> bool:
    """自动回复推文（完整流程）"""
    session = None

    try:
        if len(text) > MAX_REPLY_LENGTH:
            raise ValueError(f"回复超过 {MAX_REPLY_LENGTH} 字符限制（当前: {len(text)}）")
        if not text.strip():
            raise ValueError("回复内容不能为空")

        clean_url = _clean_tweet_url(url)

        print("\n🌐 启动 Chrome 并附着 CDP...")
        session = create_session(profile_dir=PROFILE_DIR, headless=False)
        page = session.create_task_page()
        _activate_chrome_window()

        print("🔐 检查登录状态...")
        if not session.check_login_status(HOME_URL):
            raise RuntimeError("未检测到已登录会话，请先运行 xpost post-login")
        print("✅ 已登录")

        print(f"\n📄 打开推文: {clean_url}")
        page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        _activate_chrome_window()

        print("   🔥 页面预热中...")
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        _random_delay(1500, 3000)

        try:
            page.mouse.move(
                random.randint(200, 600),
                random.randint(300, 500),
            )
            _random_delay(300, 600)
            page.mouse.wheel(0, random.randint(80, 200))
            _random_delay(500, 1000)
            page.mouse.wheel(0, random.randint(-50, -20))
            _random_delay(400, 800)
        except Exception:
            pass
        print("   ✅ 预热完成")

        _click_reply_and_wait_composer(page)

        if not input_reply_text(page, text, step_pause_ms=step_pause_ms):
            raise RuntimeError("回复文本输入失败")

        if not publish:
            print("\n✅ 草稿模式：回复已填入，未自动发送")
            return True

        if not click_reply_send(page, step_pause_ms=step_pause_ms):
            raise RuntimeError("回复发送失败")

        print("\n✅ 回复操作完成")
        return True

    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        return False
    except (ValueError, RuntimeError) as exc:
        print(f"\n❌ 操作失败: {exc}")
        logging.error("Reply 失败: %s", exc, exc_info=True)
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
        if session:
            session.close()
