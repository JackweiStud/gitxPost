#!/usr/bin/env python3
"""
xpost CLI：面向本地 Agent/自动化的 gitxPost 统一入口。

功能：
- init: 生成符合模板约束的文章骨架（可内嵌风格 Prompt）
- validate: 严格按模板规则预检
- parse: Markdown -> 结构化 JSON
- publish: X Articles 自动化草稿/发布（默认草稿）
- post: X Post 自动化草稿/发布
- post-login: 初始化 Post 登录态
- doctor: 环境与依赖检查

所有子命令均输出 JSON，便于 Agent/LLM 解析。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "pasreMarkDown" / "skills" / "x-article-publisher" / "scripts"
PROMPTS_DIR = BASE_DIR / "CreateMd" / "prompts"

STYLE_PROMPTS = {
    "zara": PROMPTS_DIR / "prompt_zara.md",
    "tech": PROMPTS_DIR / "prompt_tech.md",
    "fun": PROMPTS_DIR / "prompt_fun.md",
}

DEFAULT_SEED_IMAGES = {
    "cover.png": BASE_DIR / "CreateMd" / "images" / "cover.png",
    "demo1.png": BASE_DIR / "CreateMd" / "images" / "demo1.png",
}


def _print_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip()
    return text


def _iter_significant_lines(lines):
    in_comment = False
    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue
        if "<!--" in stripped:
            if "-->" not in stripped:
                in_comment = True
            continue
        yield idx, line


def _validate_markdown(md_path: Path):
    errors = []
    warnings = []

    if not md_path.exists():
        errors.append({"code": "E_FILE_NOT_FOUND", "message": "Markdown 文件不存在"})
        return False, errors, warnings

    content = _strip_frontmatter(_read_text(md_path))
    lines = content.splitlines()

    first_sig = None
    for line_no, line in _iter_significant_lines(lines):
        first_sig = (line_no, line)
        break

    if not first_sig:
        errors.append({"code": "E_EMPTY", "message": "Markdown 文件为空"})
        return False, errors, warnings

    title_line_no, title_line = first_sig
    if not re.match(r"^#\s+.+", title_line.strip()):
        errors.append({"code": "E_TITLE", "message": "必须以 H1 标题开头：# 标题"})

    image_re = re.compile(r"^\s*!\[[^\]]*\]\(([^)]+)\)\s*$")
    images = []
    for idx, raw in enumerate(lines, start=1):
        match = image_re.match(raw)
        if match:
            images.append({"line": idx, "path": match.group(1).strip(), "raw": raw})

    if not images:
        errors.append({"code": "E_NO_COVER", "message": "必须包含封面图（第一张图片）"})
        return False, errors, warnings

    first_image = images[0]
    if first_image["line"] < title_line_no:
        errors.append({"code": "E_COVER_BEFORE_TITLE", "message": "封面图必须在标题之后"})

    cover_path = first_image["path"]
    if not cover_path.startswith("images/"):
        errors.append({"code": "E_COVER_PATH", "message": "封面图路径必须使用 images/ 相对路径"})
    elif cover_path != "images/cover.png":
        warnings.append({"code": "W_COVER_NAME", "message": "建议封面文件名使用 images/cover.png"})

    for img in images:
        path = img["path"]
        if not path.startswith("images/"):
            errors.append({"code": "E_IMAGE_PATH", "message": f"图片路径必须使用 images/ 相对路径 (line {img['line']})"})
            continue
        abs_path = (md_path.parent / path).resolve()
        if not abs_path.exists():
            errors.append({"code": "E_IMAGE_MISSING", "message": f"图片文件不存在: {path} (line {img['line']})"})

    ok = len(errors) == 0
    return ok, errors, warnings


def _load_prompt(style: str) -> Optional[str]:
    path = STYLE_PROMPTS.get(style)
    if not path:
        return None
    if not path.exists():
        return None
    return _read_text(path)


def _build_init_content(topic: Optional[str], style: Optional[str], include_prompt: bool):
    title = topic.strip() if topic else "在这里填写标题"

    prompt_block = ""
    if include_prompt and style:
        prompt_text = _load_prompt(style)
        if prompt_text:
            prompt_block = "\n".join(
                [
                    "<!--",
                    f"STYLE: {style}",
                    f"TOPIC: {topic or ''}",
                    "PROMPT:",
                    prompt_text,
                    "-->",
                    "",
                ]
            )

    skeleton = "\n".join(
        [
            f"# {title}",
            "",
            "![封面图](images/cover.png)",
            "",
            "开场段落：直接命中痛点，说明为什么这件事重要。",
            "",
            "## 小节一",
            "",
            "写一段正文内容，解释背景或问题。",
            "",
            "![配图](images/demo1.png)",
            "",
            "## 小节二",
            "",
            "写一段正文内容，给出方法或步骤。",
            "",
            "## 结语",
            "",
            "给出行动建议或 CTA。",
            "",
            "---",
            "",
            "[@YourHandle](https://x.com/yourhandle)",
            "",
        ]
    )

    return f"{prompt_block}{skeleton}"


def _cmd_init(args):
    md_path = Path(args.md_path).expanduser().resolve()
    if md_path.exists() and not args.force:
        _print_json(
            {
                "created": False,
                "error": "文件已存在，如需覆盖请使用 --force",
                "md_path": str(md_path),
            }
        )
        return 1

    md_path.parent.mkdir(parents=True, exist_ok=True)
    images_dir = md_path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for name, seed_path in DEFAULT_SEED_IMAGES.items():
        target_path = images_dir / name
        if target_path.exists() or not seed_path.exists():
            continue
        shutil.copy2(seed_path, target_path)

    content = _build_init_content(args.topic, args.style, not args.no_prompt)
    _write_text(md_path, content)

    _print_json(
        {
            "created": True,
            "md_path": str(md_path),
            "images_dir": str(images_dir),
            "style": args.style,
            "topic": args.topic,
            "prompt_included": not args.no_prompt,
        }
    )
    return 0


def _cmd_validate(args):
    ok, errors, warnings = _validate_markdown(Path(args.md_path).expanduser().resolve())
    _print_json({"ok": ok, "errors": errors, "warnings": warnings})
    return 0 if ok else 1


def _cmd_parse(args):
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from parse_markdown import parse_markdown_file
    except Exception as exc:
        _print_json({"ok": False, "error": f"解析模块加载失败: {exc}"})
        return 1

    md_path = Path(args.md_path).expanduser().resolve()
    if not md_path.exists():
        _print_json({"ok": False, "error": "Markdown 文件不存在"})
        return 1

    try:
        result = parse_markdown_file(str(md_path))
        _print_json(result)
        return 0
    except Exception as exc:
        _print_json({"ok": False, "error": f"解析失败: {exc}"})
        return 1


def _cmd_publish(args):
    md_path = Path(args.md_path).expanduser().resolve()
    if not md_path.exists():
        _print_json({"ok": False, "error": "Markdown 文件不存在"})
        return 1

    if args.profile_dir:
        os.environ["XPOST_PROFILE_DIR"] = str(Path(args.profile_dir).expanduser().resolve())

    if args.no_wait:
        os.environ["XPOST_NO_WAIT"] = "1"

    if args.chrome_version_main:
        os.environ["XPOST_CHROME_VERSION_MAIN"] = str(args.chrome_version_main)

    sys.path.insert(0, str(BASE_DIR))
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from parse_markdown import parse_markdown_file
    except Exception as exc:
        _print_json({"ok": False, "error": f"解析模块加载失败: {exc}"})
        return 1

    try:
        import auto_publish_uc
    except Exception as exc:
        _print_json({"ok": False, "error": f"发布模块加载失败: {exc}"})
        return 1

    start_ts = time.time()
    try:
        parse_result = parse_markdown_file(str(md_path))
    except Exception as exc:
        _print_json({"ok": False, "error": f"解析失败: {exc}"})
        return 1
    parse_ms = int((time.time() - start_ts) * 1000)

    missing_images = []
    if parse_result.get("cover_exists") is False and parse_result.get("cover_image"):
        missing_images.append(parse_result["cover_image"])
    for img in parse_result.get("content_images", []):
        if not img.get("exists", True):
            missing_images.append(img.get("path"))

    publish_start = time.time()
    try:
        success = auto_publish_uc.auto_publish_article(str(md_path), publish=args.publish)
        publish_ms = int((time.time() - publish_start) * 1000)
        total_ms = int((time.time() - start_ts) * 1000)
        _print_json(
            {
                "ok": success,
                "mode": "publish" if args.publish else "draft",
                "missing_images": missing_images,
                "missing_images_count": len(missing_images),
                "timings": {
                    "parse_ms": parse_ms,
                    "publish_ms": publish_ms,
                    "total_ms": total_ms,
                },
            }
        )
        return 0 if success else 1
    except Exception as exc:
        _print_json({"ok": False, "error": f"发布失败: {exc}"})
        return 1


def _cmd_post(args):
    """发布 X Post（短文）"""
    # 设置环境变量
    if args.profile_dir:
        os.environ["XPOST_PROFILE_DIR"] = str(Path(args.profile_dir).expanduser().resolve())

    if args.no_wait:
        os.environ["XPOST_NO_WAIT"] = "1"

    if args.remote_debugging_port:
        os.environ["XPOST_REMOTE_DEBUGGING_PORT"] = str(args.remote_debugging_port)
    if args.observe_ms is not None:
        os.environ["XPOST_STEP_PAUSE_MS"] = str(args.observe_ms)

    # 加载发布模块
    sys.path.insert(0, str(BASE_DIR))
    try:
        from auto_publish_post import auto_publish_post
    except Exception as exc:
        _print_json({"ok": False, "error": f"Post 发布模块加载失败: {exc}"})
        return 1

    # 验证图片文件存在性
    images = args.images or []
    missing_images = []
    if images:
        for img_path in images:
            abs_path = Path(img_path).expanduser().resolve()
            if not abs_path.exists():
                missing_images.append(str(img_path))

    if missing_images:
        _print_json(
            {
                "ok": False,
                "error": "部分图片文件不存在",
                "missing_images": missing_images,
            }
        )
        return 1

    # 转换为绝对路径
    abs_images = [str(Path(img).expanduser().resolve()) for img in images] if images else None

    # 执行发布
    start_ts = time.time()
    try:
        success = auto_publish_post(
            text=args.text,
            images=abs_images,
            publish=args.publish,
            wait_after=not args.no_wait,
            step_pause_ms=args.observe_ms,
        )
        total_ms = int((time.time() - start_ts) * 1000)

        _print_json(
            {
                "ok": success,
                "mode": "publish" if args.publish else "draft",
                "text_length": len(args.text),
                "images_count": len(images),
                "timings": {
                    "total_ms": total_ms,
                },
            }
        )
        return 0 if success else 1

    except ValueError as exc:
        _print_json({"ok": False, "error": f"输入验证失败: {exc}"})
        return 1
    except Exception as exc:
        _print_json({"ok": False, "error": f"发布失败: {exc}"})
        return 1


def _cmd_post_login(args):
    if args.profile_dir:
        os.environ["XPOST_PROFILE_DIR"] = str(Path(args.profile_dir).expanduser().resolve())
    if args.remote_debugging_port:
        os.environ["XPOST_REMOTE_DEBUGGING_PORT"] = str(args.remote_debugging_port)

    sys.path.insert(0, str(BASE_DIR))
    try:
        from auto_publish_post import initialize_login_session
    except Exception as exc:
        _print_json({"ok": False, "error": f"Post 登录初始化模块加载失败: {exc}"})
        return 1

    start_ts = time.time()
    try:
        success = initialize_login_session(timeout=args.login_timeout)
        total_ms = int((time.time() - start_ts) * 1000)
        _print_json(
            {
                "ok": success,
                "mode": "login_setup",
                "timings": {
                    "total_ms": total_ms,
                },
            }
        )
        return 0 if success else 1
    except Exception as exc:
        _print_json({"ok": False, "error": f"登录初始化失败: {exc}"})
        return 1


def _detect_chrome_version():
    chrome_bin = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome_bin.exists():
        return None
    try:
        result = subprocess.run([str(chrome_bin), "--version"], capture_output=True, text=True, timeout=5)
        version_str = result.stdout.strip() or result.stderr.strip()
        match = re.search(r"(\d+)\.", version_str)
        major = int(match.group(1)) if match else None
        return {"raw": version_str, "major": major}
    except Exception:
        return None


def _cmd_doctor(_args):
    deps = {}
    for mod in [
        "patchright",
        "PIL",
    ]:
        try:
            __import__(mod)
            deps[mod] = True
        except Exception:
            deps[mod] = False

    clipboard_ok = False
    try:
        __import__("AppKit")
        clipboard_ok = True
    except Exception:
        clipboard_ok = False

    chrome = _detect_chrome_version()
    python_ok = sys.version_info >= (3, 9)
    platform_ok = sys.platform == "darwin"

    ok = python_ok and platform_ok and all(deps.values()) and clipboard_ok and chrome is not None
    notes = []
    missing_deps = [k for k, v in deps.items() if not v]
    if missing_deps:
        notes.append("检测到依赖缺失，建议先激活虚拟环境并安装 requirements.txt")
    if deps.get("patchright"):
        notes.append("Article、Post、Grok 当前都使用真实 Google Chrome profile + Patchright CDP 附着")
    if not clipboard_ok and sys.platform == "darwin":
        notes.append("剪贴板依赖缺失，确认已安装 pyobjc-framework-Cocoa")
    if not platform_ok:
        notes.append("当前脚本为 macOS 专用版")

    _print_json(
        {
            "ok": ok,
            "platform": sys.platform,
            "python": {
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "ok": python_ok,
            },
            "chrome": chrome,
            "deps": deps,
            "clipboard_ok": clipboard_ok,
            "notes": notes,
        }
    )
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(prog="xpost", description="gitxPost local CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a new article skeleton")
    p_init.add_argument("md_path", help="Target markdown path")
    p_init.add_argument("--topic", help="Article topic for title")
    p_init.add_argument("--style", choices=sorted(STYLE_PROMPTS.keys()), help="Prompt style")
    p_init.add_argument("--no-prompt", action="store_true", help="Do not embed prompt block")
    p_init.add_argument("--force", action="store_true", help="Overwrite if file exists")
    p_init.set_defaults(func=_cmd_init)

    p_validate = sub.add_parser("validate", help="Validate markdown format")
    p_validate.add_argument("md_path", help="Markdown path")
    p_validate.set_defaults(func=_cmd_validate)

    p_parse = sub.add_parser("parse", help="Parse markdown to JSON")
    p_parse.add_argument("md_path", help="Markdown path")
    p_parse.set_defaults(func=_cmd_parse)

    p_publish = sub.add_parser("publish", help="Publish or save draft")
    p_publish.add_argument("md_path", help="Markdown path")
    p_publish.add_argument("--publish", action="store_true", help="Publish directly")
    p_publish.add_argument("--profile-dir", help="Chrome profile directory")
    p_publish.add_argument("--no-wait", action="store_true", help="Do not wait for Enter in draft mode")
    p_publish.add_argument("--chrome-version-main", type=int, help="Chrome major version override")
    p_publish.set_defaults(func=_cmd_publish)

    p_post = sub.add_parser("post", help="Publish X Post (short text)")
    p_post.add_argument("text", help="Post text content (max 280 characters)")
    p_post.add_argument("--images", nargs="+", help="Image paths (max 4)")
    p_post.add_argument("--publish", action="store_true", help="Publish directly (default: draft)")
    p_post.add_argument("--profile-dir", help="Chrome profile directory")
    p_post.add_argument("--no-wait", action="store_true", help="Do not wait after completion")
    p_post.add_argument("--remote-debugging-port", type=int, help="Chrome CDP port override")
    p_post.add_argument("--observe-ms", type=int, default=900, help="Pause after key steps so the UI is visible")
    p_post.set_defaults(func=_cmd_post)

    p_post_login = sub.add_parser("post-login", help="Initialize and persist X login session for post")
    p_post_login.add_argument("--profile-dir", help="Chrome profile directory for post session")
    p_post_login.add_argument("--login-timeout", type=int, default=600, help="Manual login timeout in seconds")
    p_post_login.add_argument("--remote-debugging-port", type=int, help="Chrome CDP port override")
    p_post_login.set_defaults(func=_cmd_post_login)

    p_doctor = sub.add_parser("doctor", help="Check environment and deps")
    p_doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
