#!/usr/bin/env python3
"""End-to-end regression for the article workflow in web UI.

This script exercises:
1. Create article from the list page.
2. Edit, auto-save, one-click generate, and publish.
3. Return to the list and create a second article.
4. Verify the editor opens the newly created article instead of reusing the old one.

Run from anywhere:
  python3 web/ui/e2e/article_workflow_regression.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

try:
    from patchright.sync_api import sync_playwright
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "patchright is required for this regression script. "
        "Install the project dependencies first."
    ) from exc


DEFAULT_API_BASE = "http://127.0.0.1:8900"
DEFAULT_UI_BASE = "http://127.0.0.1:5900"
DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def api_request(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def wait_for_article(api_base: str, article_id: str, predicate, timeout_s: int = 180) -> dict:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        last = api_request("GET", f"{api_base}/api/articles/{article_id}")
        article = last["article"]
        if predicate(article):
            return last
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for article state: {article_id}. Last={last}")


def unique_title(prefix: str) -> str:
    return f"{prefix} {int(time.time() * 1000)}"


def open_list_page(page, ui_base: str) -> None:
    page.goto(f"{ui_base}/articles", wait_until="networkidle")
    page.wait_for_selector("button", state="visible")


def create_article_via_api(api_base: str, title: str) -> str:
    result = api_request("POST", f"{api_base}/api/articles", {"title": title})
    return result["article_id"]


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r}, actual={actual!r}")


def run(args: argparse.Namespace) -> dict:
    chrome_path = os.environ.get("CHROME_PATH", DEFAULT_CHROME)
    launch_kwargs = {"headless": not args.headed}
    if Path(chrome_path).exists():
        launch_kwargs["executable_path"] = chrome_path

    summary = {
        "first_article": None,
        "second_article": None,
        "published": False,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={"width": 1440, "height": 1200})
        page = context.new_page()
        page.set_default_timeout(30000)

        # Quiet down noisy console output, but keep errors if they happen.
        page.on("console", lambda msg: print(f"[console:{msg.type}] {msg.text}", file=sys.stderr) if msg.type in {"error", "warning"} else None)

        first_title = unique_title("E2E workflow")
        second_title = unique_title("E2E follow-up")

        first_article_id = create_article_via_api(args.api_base, first_title)
        open_list_page(page, args.ui_base)
        page.locator(".article-card", has_text=first_title).get_by_title("继续编辑").click()
        page.wait_for_url(re.compile(r".*/articles/[^/]+$"))
        summary["first_article"] = first_article_id

        assert_equal(page.url.rstrip("/").split("/")[-1], first_article_id, "First article route mismatch")
        assert_equal(page.locator("input.title-input").input_value(), first_title, "First article title mismatch")

        # Exercise edit + autosave.
        page.locator("select.style-selector").select_option("tech")
        page.locator("textarea.editor-textarea").fill(
            "这是一段用于回归测试的草稿内容。\n"
            "我们会先触发自动保存，再执行一键生成。"
        )
        page.wait_for_function(
            """() => {
              const el = document.querySelector('.save-status');
              return !!el && el.innerText.includes('已保存');
            }""",
            timeout=20000,
        )

        # One-click generation from title + edited draft.
        page.get_by_role("button", name="一键生成").click()
        page.wait_for_selector(".progress-indicator")
        wait_for_article(args.api_base, first_article_id, lambda article: article["step"] == "content" and len(article.get("content", "")) > 100)
        page.reload(wait_until="networkidle")
        page.wait_for_selector("input.title-input")
        assert_equal(page.locator("input.title-input").input_value(), first_title, "First article title changed after generation")
        page.wait_for_function(
            """() => {
              return Array.from(document.querySelectorAll('button')).some(
                btn => btn.textContent && btn.textContent.includes('发布文章')
              );
            }""",
            timeout=60000,
        )

        # Publish the article and wait for backend confirmation.
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="发布文章").click()
        wait_for_article(args.api_base, first_article_id, lambda article: article["status"] == "published" and article.get("published_at"))
        summary["published"] = True

        # Return to the list and create a second article. This verifies the editor reloads
        # the new route instead of keeping the previously published article alive.
        second_article_id = create_article_via_api(args.api_base, second_title)
        page.goto(f"{args.ui_base}/articles", wait_until="networkidle")
        page.wait_for_selector("button", state="visible")
        page.locator(".article-card", has_text=second_title).get_by_title("继续编辑").click()
        page.wait_for_url(re.compile(r".*/articles/[^/]+$"))
        summary["second_article"] = second_article_id

        assert_equal(page.url.rstrip("/").split("/")[-1], second_article_id, "Second article route mismatch")
        assert_equal(page.locator("input.title-input").input_value(), second_title, "Second article title mismatch")
        assert second_article_id != first_article_id, "Article IDs should be unique"

        if not args.keep_open:
            browser.close()

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Article workflow regression for web UI")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Backend API base URL")
    parser.add_argument("--ui-base", default=DEFAULT_UI_BASE, help="Frontend UI base URL")
    parser.add_argument("--headed", action="store_true", help="Run the browser headed")
    parser.add_argument("--keep-open", action="store_true", help="Keep the browser open at the end")
    args = parser.parse_args()

    try:
        summary = run(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"ok": True, "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
