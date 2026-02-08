#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run_xpost(args):
    result = subprocess.run(
        ["xpost"] + args,
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"ok": False, "error": "非 JSON 输出", "stdout": result.stdout, "stderr": result.stderr}
    return result.returncode, data


def _is_md_path(text: str) -> bool:
    return text.endswith(".md") or text.startswith("/") or text.startswith("~")


def _default_md_path():
    ts = time.strftime("%Y%m%d_%H%M%S")
    return Path.cwd() / "CreateMd" / f"article_{ts}.md"


def main():
    parser = argparse.ArgumentParser(description="Agent example: init -> validate -> publish")
    parser.add_argument("input", help="Markdown 路径或主题文本")
    parser.add_argument("--style", default="zara", choices=["zara", "tech", "fun"], help="写作风格")
    args = parser.parse_args()

    raw_input = args.input
    if _is_md_path(raw_input) or Path(raw_input).expanduser().exists():
        md_path = Path(raw_input).expanduser().resolve()
        topic = None
    else:
        md_path = _default_md_path().resolve()
        topic = raw_input

    # 1) init（如果文件不存在则生成骨架）
    if not md_path.exists():
        init_args = ["init", str(md_path), "--style", args.style]
        if topic:
            init_args += ["--topic", topic]
        code, init_res = run_xpost(init_args)
        print(json.dumps({"step": "init", "result": init_res}, ensure_ascii=False, indent=2))
        if code != 0:
            return code

    # 2) validate
    code, val_res = run_xpost(["validate", str(md_path)])
    print(json.dumps({"step": "validate", "result": val_res}, ensure_ascii=False, indent=2))
    if code != 0:
        return code

    # 3) publish（默认草稿）
    code, pub_res = run_xpost(["publish", str(md_path), "--no-wait"])
    print(json.dumps({"step": "publish", "result": pub_res}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
