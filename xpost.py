#!/usr/bin/env python3
"""
xpost CLI：面向本地 Agent/自动化的 gitxPost 统一入口。

功能：
- init: 生成符合模板约束的文章骨架（可内嵌风格 Prompt）
- generate: 调用 LLM API 将文章骨架扩写成真实 Markdown 成文
- validate: 严格按模板规则预检
- parse: Markdown -> 结构化 JSON
- publish: X Articles 自动化草稿/发布（默认草稿）
- post: X Post 自动化草稿/发布
- post-login: 初始化 Post 登录态
- radar-scan: 运行 X 雷达扫描
- radar-analyze: 运行 X 雷达分析
- radar-daily: 基于扫描结果生成 Radar 日报
- radar-weekly: 基于分析结果生成 Radar 周报
- radar-accounts: 管理 X 雷达监控账号
- reply: 回复指定推文（提取正文 / 逐字输入 / 发送）
- reply-extract: 仅提取推文正文（不回复）
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
from datetime import datetime
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "article_tooling" / "scripts"
PROMPTS_DIR = BASE_DIR / "content" / "prompts"
XINFO_DIR = BASE_DIR / "xinfo"
XINFO_LOG_DIR = XINFO_DIR / "log"
XINFO_DAY_DIR = XINFO_LOG_DIR / "day"
XINFO_WEEK_DIR = XINFO_LOG_DIR / "week"
XINFO_RUNTIME_DIR = XINFO_LOG_DIR / "runtime"

STYLE_PROMPTS = {
    "zara": PROMPTS_DIR / "prompt_zara.md",
    "tech": PROMPTS_DIR / "prompt_tech.md",
    "fun": PROMPTS_DIR / "prompt_fun.md",
}

DEFAULT_SEED_IMAGES = {
    "cover.png": BASE_DIR / "content" / "examples" / "images" / "cover.png",
    "demo1.png": BASE_DIR / "content" / "examples" / "images" / "demo1.png",
}

PLACEHOLDER_HINTS = [
    "开场段落：直接命中痛点",
    "写一段正文内容",
    "给出行动建议或 CTA",
    "[在这里填入你的主题",
]

# radar-daily 默认上限（低于旧版 100k，避免与部分备用网关不兼容；可用 CLI 调大）
DEFAULT_RADAR_DAILY_MAX_TOKENS = 16384


class RadarReportGenerationError(RuntimeError):
    def __init__(self, message: str, attempt_logs=None):
        super().__init__(message)
        self.attempt_logs = attempt_logs or []


def _load_project_dotenv(dotenv_path: Path):
    if not dotenv_path.exists():
        return
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        os.environ[key] = value


_load_project_dotenv(BASE_DIR / ".env")


def _print_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def _append_jsonl(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _runtime_log_path(command: str) -> Path:
    return XINFO_RUNTIME_DIR / f"{_today_str()}_{command}.jsonl"


def _truncate_text(text: Optional[str], limit: int = 1500) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "...<truncated>"


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

    for hint in PLACEHOLDER_HINTS:
        if hint in content:
            warnings.append({"code": "W_TEMPLATE_PLACEHOLDER", "message": f"检测到模板占位内容尚未替换: {hint}"})

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


def _extract_prompt_block(md_text: str):
    if not md_text.lstrip().startswith("<!--"):
        return None
    match = re.match(r"\s*<!--\n(.*?)\n-->\s*", md_text, re.S)
    if not match:
        return None
    raw_block = match.group(0)
    body = match.group(1)

    style = None
    topic = None
    prompt_lines = []
    in_prompt = False
    for line in body.splitlines():
        if line.startswith("STYLE:"):
            style = line.split(":", 1)[1].strip() or None
            continue
        if line.startswith("TOPIC:"):
            topic = line.split(":", 1)[1].strip() or None
            continue
        if line.strip() == "PROMPT:":
            in_prompt = True
            continue
        if in_prompt:
            prompt_lines.append(line)

    return {
        "raw_block": raw_block,
        "style": style,
        "topic": topic,
        "prompt": "\n".join(prompt_lines).strip(),
    }


def _strip_prompt_block(md_text: str) -> str:
    prompt_meta = _extract_prompt_block(md_text)
    if not prompt_meta:
        return md_text
    return md_text.replace(prompt_meta["raw_block"], "", 1).lstrip()


def _extract_h1_title(md_text: str) -> Optional[str]:
    for _, line in _iter_significant_lines(md_text.splitlines(True)):
        if re.match(r"^#\s+.+", line.strip()):
            return re.sub(r"^#\s+", "", line.strip())
    return None


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    return stripped.strip()


def _resolve_generate_config(args):
    api_key = (
        os.environ.get("XPOST_LLM_API_KEY")
    )
    api_url = (
        args.api_url
        or os.environ.get("XPOST_LLM_API_URL")
        or "https://tokenmax.vip/v1/messages"
    )
    model = (
        args.model
        or os.environ.get("XPOST_LLM_MODEL")
        or "claude-sonnet-4-6"
    )
    fb_url = os.environ.get("XPOST_LLM_FALLBACK_API_URL")
    fb_key = os.environ.get("XPOST_LLM_FALLBACK_API_KEY")
    fb_model = os.environ.get("XPOST_LLM_FALLBACK_MODEL")
    chain = _build_llm_chain(
        api_url,
        api_key,
        model,
        label_primary="primary",
        fallback_url=fb_url,
        fallback_key=fb_key,
        fallback_model=fb_model,
        label_fallback="fallback",
    )
    return {
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
        "llm_chain": chain,
    }


def _resolve_radar_llm_config(args):
    api_key = os.environ.get("XPOST_LLM_API_KEY")
    api_url = (
        args.api_url
        or os.environ.get("XPOST_LLM_API_URL")
        or "https://tokenmax.vip/v1/messages"
    )
    model = (
        args.model
        or os.environ.get("XPOST_RADAR_LLM_MODEL")
        or os.environ.get("XPOST_LLM_MODEL")
        or "claude-opus-4-6"
    )
    fb_url = os.environ.get("XPOST_LLM_FALLBACK_API_URL")
    fb_key = os.environ.get("XPOST_LLM_FALLBACK_API_KEY")
    fb_model = (
        os.environ.get("XPOST_RADAR_LLM_FALLBACK_MODEL")
        or os.environ.get("XPOST_LLM_FALLBACK_MODEL")
    )
    chain = _build_llm_chain(
        api_url,
        api_key,
        model,
        label_primary="primary",
        fallback_url=fb_url,
        fallback_key=fb_key,
        fallback_model=fb_model,
        label_fallback="fallback",
    )
    return {
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
        "llm_chain": chain,
    }


def _infer_llm_api_kind(api_url: str) -> str:
    u = (api_url or "").lower()
    if "/messages" in u:
        return "anthropic"
    return "openai"


def _openai_chat_completions_url(api_url: str) -> str:
    url = (api_url or "").strip().rstrip("/")
    if not url:
        return url
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return url


def _build_llm_chain(
    api_url: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
    *,
    label_primary: str,
    fallback_url: Optional[str],
    fallback_key: Optional[str],
    fallback_model: Optional[str],
    label_fallback: str,
):
    chain = []
    if api_key and api_url and model:
        chain.append(
            {
                "label": label_primary,
                "api_url": api_url,
                "api_key": api_key,
                "model": model,
                "kind": _infer_llm_api_kind(api_url),
            }
        )
    if fallback_key and fallback_url and fallback_model:
        fb_kind = os.environ.get("XPOST_LLM_FALLBACK_API_KIND") or "openai"
        chain.append(
            {
                "label": label_fallback,
                "api_url": fallback_url,
                "api_key": fallback_key,
                "model": fallback_model,
                "kind": fb_kind.strip().lower() if fb_kind else "openai",
            }
        )
    return chain


def _build_generation_prompt(md_path: Path, raw_markdown: str, style: Optional[str], topic: Optional[str]):
    embedded = _extract_prompt_block(raw_markdown)
    prompt_text = embedded["prompt"] if embedded and embedded.get("prompt") else None
    resolved_style = style or (embedded.get("style") if embedded else None)
    resolved_topic = topic or (embedded.get("topic") if embedded else None) or _extract_h1_title(raw_markdown) or md_path.stem
    if not prompt_text and resolved_style:
        prompt_text = _load_prompt(resolved_style)

    if not prompt_text:
        raise ValueError("未找到可用 Prompt。请先用 xpost init --style 生成骨架，或在 generate 时显式传入 --style。")

    skeleton = _strip_prompt_block(raw_markdown)
    image_lines = re.findall(r"^\s*!\[[^\]]*\]\(([^)]+)\)\s*$", skeleton, re.M)
    footer_match = re.search(r"\[@[^\]]+\]\([^)]+\)", skeleton)
    footer_text = footer_match.group(0) if footer_match else "[@YourHandle](https://x.com/yourhandle)"

    return "\n".join(
        [
            "你是一位擅长写 X Article 的专业作者。",
            "请基于给定的风格 Prompt 和当前 Markdown 骨架，输出一份可以直接发布的完整 Markdown 文章。",
            "",
            "严格要求：",
            "1. 只输出最终 Markdown，不要解释，不要代码围栏。",
            "2. 必须以 H1 标题开头。",
            "3. 保留图片占位位置，且图片路径必须继续使用相对路径。",
            "4. 第一张图片必须保留为封面图。",
            "5. 替换掉所有模板占位句子，写成真实、完整、可读的正文。",
            "6. 保留结尾链接结构；若需更新签名，可只改链接文本，不改 Markdown 结构。",
            "7. 默认使用中文输出；若主题明显为英文，再酌情使用英文。",
            "",
            f"主题：{resolved_topic}",
            f"风格：{resolved_style or 'embedded'}",
            f"图片路径：{', '.join(image_lines) if image_lines else '无'}",
            f"结尾链接：{footer_text}",
            "",
            "风格 Prompt：",
            prompt_text,
            "",
            "当前 Markdown 骨架：",
            skeleton,
        ]
    )


def _call_messages_api(
    api_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    *,
    return_debug: bool = False,
):
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.6,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [
                "curl",
                "-sS",
                "--http1.1",
                "--retry",
                "2",
                "--retry-all-errors",
                "--connect-timeout",
                "30",
                "-X",
                "POST",
                api_url,
                "-H",
                f"Authorization: Bearer {api_key}",
                "-H",
                "Content-Type: application/json",
                "-H",
                "Anthropic-Version: 2023-06-01",
                "-d",
                payload_json,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM API 请求失败: {exc}") from exc

    if proc.returncode != 0:
        raise RuntimeError(f"curl 请求失败: {proc.stderr.strip() or proc.stdout.strip()}")

    raw = proc.stdout
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"LLM API 返回非 JSON: {raw[:300]}") from exc

    if data.get("type") != "message":
        err = data.get("error", {}).get("message") or data.get("message") or raw[:300]
        raise RuntimeError(f"LLM API 返回异常: {err}")

    content_items = data.get("content", [])
    parts = []
    content_types = []
    for item in content_items:
        content_type = item.get("type")
        if content_type:
            content_types.append(content_type)
        if content_type == "text":
            parts.append(item.get("text", ""))
    text = "\n".join(parts).strip()
    if return_debug:
        return {
            "text": _strip_markdown_fences(text) if text else "",
            "raw_response": raw,
            "content_types": content_types,
        }
    if not text:
        raise RuntimeError("LLM 返回为空")
    return _strip_markdown_fences(text)


def _call_openai_chat_api(
    api_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    *,
    return_debug: bool = False,
):
    endpoint = _openai_chat_completions_url(api_url)
    if not endpoint:
        raise RuntimeError("OpenAI 兼容 LLM URL 为空")
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.6,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [
                "curl",
                "-sS",
                "--http1.1",
                "--retry",
                "2",
                "--retry-all-errors",
                "--connect-timeout",
                "30",
                "-X",
                "POST",
                endpoint,
                "-H",
                f"Authorization: Bearer {api_key}",
                "-H",
                "Content-Type: application/json",
                "-d",
                payload_json,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM API 请求失败: {exc}") from exc

    if proc.returncode != 0:
        raise RuntimeError(f"curl 请求失败: {proc.stderr.strip() or proc.stdout.strip()}")

    raw = proc.stdout
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"LLM API 返回非 JSON: {raw[:300]}") from exc

    err_obj = data.get("error")
    if err_obj:
        msg = err_obj.get("message") if isinstance(err_obj, dict) else str(err_obj)
        raise RuntimeError(f"LLM API 返回异常: {msg or raw[:300]}")

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"LLM API 返回无 choices: {raw[:300]}")

    msg = choices[0].get("message", {}) or {}
    content = msg.get("content", "")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        text = "\n".join(parts).strip()
    else:
        text = str(content or "").strip()

    content_types = ["text"] if text else []
    if return_debug:
        return {
            "text": _strip_markdown_fences(text) if text else "",
            "raw_response": raw,
            "content_types": content_types,
        }
    if not text:
        raise RuntimeError("LLM 返回为空")
    return _strip_markdown_fences(text)


def _effective_max_tokens_for_spec(spec: dict, max_tokens: int) -> int:
    """备用链路（label=fallback）自动压低 max_tokens，适配 Gemini 等 OpenAI 兼容网关。"""
    if spec.get("label") != "fallback":
        return max_tokens
    raw = os.environ.get("XPOST_LLM_FALLBACK_MAX_TOKENS", "8192")
    try:
        cap = int(raw)
    except ValueError:
        cap = 8192
    cap = max(1, cap)
    return min(max_tokens, cap)


def _call_llm_spec(
    spec: dict,
    prompt: str,
    max_tokens: int,
    *,
    return_debug: bool = False,
):
    eff_max = _effective_max_tokens_for_spec(spec, max_tokens)
    kind = (spec.get("kind") or _infer_llm_api_kind(spec.get("api_url", ""))).lower()
    if kind == "anthropic":
        return _call_messages_api(
            spec["api_url"],
            spec["api_key"],
            spec["model"],
            prompt,
            eff_max,
            return_debug=return_debug,
        )
    return _call_openai_chat_api(
        spec["api_url"],
        spec["api_key"],
        spec["model"],
        prompt,
        eff_max,
        return_debug=return_debug,
    )


def _call_llm_with_fallback(
    chain: list,
    prompt: str,
    max_tokens: int,
    *,
    return_debug: bool = False,
):
    if not chain:
        raise RuntimeError("未配置任何 LLM 端点")
    errors = []
    for spec in chain:
        try:
            out = _call_llm_spec(spec, prompt, max_tokens, return_debug=return_debug)
            meta = {
                "route": spec.get("label"),
                "model": spec.get("model"),
                "api_url": spec.get("api_url"),
            }
            return out, meta
        except Exception as exc:
            label = spec.get("label") or "?"
            errors.append(f"{label}: {exc}")
    raise RuntimeError("所有 LLM 端点均失败: " + " | ".join(errors))


def _parse_json_response(raw_text: str):
    text = _strip_markdown_fences(raw_text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            return obj
        except Exception:
            continue
    raise ValueError("LLM 返回无法解析为 JSON")


def _normalize_radar_report_payload(raw_text: str):
    try:
        parsed = _parse_json_response(raw_text)
    except Exception:
        return {
            "markdown": raw_text.strip() if _looks_like_markdown_report(raw_text) else "",
            "actions": [],
        }

    if isinstance(parsed, str):
        return {
            "markdown": parsed.strip(),
            "actions": [],
        }

    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回格式异常：不是对象")

    markdown = (
        parsed.get("markdown")
        or parsed.get("report")
        or parsed.get("content")
        or parsed.get("daily_markdown")
        or parsed.get("weekly_markdown")
        or ""
    )
    actions = parsed.get("actions")
    if actions is None:
        actions = parsed.get("new_actions", [])
    if not isinstance(actions, list):
        actions = []

    return {
        "markdown": str(markdown).strip(),
        "actions": actions,
    }


def _extract_markdown_from_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""
    normalized = _normalize_radar_report_payload(text)
    markdown = (normalized.get("markdown") or "").strip()
    return markdown if _looks_like_markdown_report(markdown) else ""


def _looks_like_markdown_report(text: str) -> bool:
    sample = (text or "").strip()
    if not sample:
        return False
    markers = [
        "📅 ",
        "📊 ",
        "## ",
        "### ",
        "原文↗",
        "值得试用的新工具/产品",
        "本周热点话题 Top5",
    ]
    return any(marker in sample for marker in markers)


def _generate_radar_report(prompt: str, llm_chain: list, max_tokens: int):
    attempts = [
        {
            "label": "json",
            "prompt": prompt,
            "mode": "json",
        },
        {
            "label": "strict_json",
            "prompt": prompt
            + "\n\n补充要求：如果上一次没有严格按 JSON 返回，这一次请只返回 JSON 对象，并确保 `markdown` 字段非空。",
            "mode": "json",
        },
        {
            "label": "markdown_fallback",
            "prompt": prompt
            + "\n\n最终兜底要求：如果你无法稳定返回 JSON，请直接只返回完整 Markdown 正文，不要 JSON，不要解释，不要代码围栏。",
            "mode": "markdown",
        },
    ]
    last_error = None
    attempt_logs = []
    for attempt in attempts:
        try:
            response, llm_meta = _call_llm_with_fallback(
                llm_chain,
                attempt["prompt"],
                max_tokens,
                return_debug=True,
            )
            raw_text = response["text"]
            if attempt["mode"] == "markdown":
                payload = {
                    "markdown": raw_text.strip() if _looks_like_markdown_report(raw_text) else "",
                    "actions": [],
                }
            else:
                payload = _normalize_radar_report_payload(raw_text)
                if not payload.get("markdown") and _looks_like_markdown_report(raw_text):
                    payload["markdown"] = raw_text.strip()
            if payload.get("markdown"):
                attempt_logs.append(
                    {
                        "label": attempt["label"],
                        "ok": True,
                        "content_types": response.get("content_types", []),
                        "markdown_len": len(payload.get("markdown", "")),
                        "raw_preview": _truncate_text(response.get("raw_response")),
                        "llm_route": llm_meta.get("route"),
                        "llm_model": llm_meta.get("model"),
                    }
                )
                return payload, attempt_logs, llm_meta
            last_error = RuntimeError("LLM 未返回 markdown")
            attempt_logs.append(
                {
                    "label": attempt["label"],
                    "ok": False,
                    "error": str(last_error),
                    "content_types": response.get("content_types", []),
                    "raw_preview": _truncate_text(response.get("raw_response")),
                    "llm_route": llm_meta.get("route"),
                }
            )
        except Exception as exc:
            last_error = exc
            attempt_logs.append(
                {
                    "label": attempt["label"],
                    "ok": False,
                    "error": str(exc),
                }
            )
    if isinstance(last_error, Exception):
        raise RadarReportGenerationError(str(last_error), attempt_logs) from last_error
    raise RadarReportGenerationError("LLM 返回异常", attempt_logs)


def _read_json_file(path: Path, default=None):
    if not path.exists():
        if default is None:
            raise FileNotFoundError(str(path))
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_file(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _default_interests_payload():
    return {
        "focus": [],
        "recent_context": [],
        "ignore": [],
    }


def _default_actions_payload():
    return {
        "actions": [],
    }


def _record_radar_runtime(command: str, payload: dict) -> str:
    log_path = _runtime_log_path(command)
    entry = {
        "timestamp": _now_str(),
        **payload,
    }
    _append_jsonl(log_path, entry)
    return str(log_path)


def _ensure_support_file(path: Path, default_payload):
    if path.exists():
        return False
    _write_json_file(path, default_payload)
    return True


def _append_actions(actions_path: Path, new_actions):
    payload = _read_json_file(actions_path, default=_default_actions_payload())
    items = payload.setdefault("actions", [])
    added = []
    today = _today_str()
    for item in new_actions or []:
        action = (item.get("action") or "").strip()
        if not action:
            continue
        normalized = {
            "action": action,
            "date": item.get("date") or today,
            "status": item.get("status") or "pending",
            "source_link": item.get("source_link") or "",
            "source_account": item.get("source_account") or "",
        }
        items.append(normalized)
        added.append(normalized)
    _write_json_file(actions_path, payload)
    return added


def _wrap_report_markdown(body: str, metadata: dict):
    frontmatter = ["---"]
    for key, value in metadata.items():
        frontmatter.append(f'{key}: "{str(value).replace("\"", "\\\"")}"')
    frontmatter.append("---")
    frontmatter.append("")
    return "\n".join(frontmatter) + body.strip() + "\n"


def _build_radar_daily_prompt(result_payload: dict, interests_payload: dict):
    summary = result_payload.get("summary", {})
    preview = summary.get("new_ideas_preview", [])
    scan_meta = {
        "scan_time": summary.get("scan_time"),
        "account_stats": summary.get("account_stats", {}),
        "new_tweets_count": summary.get("new_tweets_count"),
        "new_originals_count": summary.get("new_originals_count"),
        "sampled_preview_count": summary.get("sampled_preview_count", len(preview)),
        "status": summary.get("status"),
    }
    return "\n".join(
        [
            "你是一个严格基于真实 X 扫描结果生成中文日报的分析助手。",
            "禁止编造任何链接、账号、产品、数据或观点；只能使用输入 JSON 中真实存在的字段。",
            "请返回 JSON 对象，不要解释，不要代码围栏。",
            "",
            "返回格式：",
            "{",
            '  "markdown": "完整日报 Markdown 文本",',
            '  "actions": [',
            '    {"action":"具体行动","source_link":"原文链接","source_account":"@账号"}',
            "  ]",
            "}",
            "",
            "日报要求：",
            "1. 顶部使用 `📅 YYYY年M月D日`。",
            "2. 日期下面必须先输出一行 `🔎 数据范围`，明确写出：扫描账号数、成功账号数、新推文数、原创数、预览采样数。",
            "3. 先输出 `🌐 今日热议话题`，只保留 3-4 个真实话题簇；每条格式固定为：`• 话题名：一句话焦点。（N 条）`，不要输出“主要来源”或账号列表。",
            "4. 必须完整阅读 `new_ideas_preview` 全部条目后再聚类，不要只取前几条，不要只围绕单一账号下结论。",
            "5. 再按需要输出这些中文分类：`🔧 值得试用的新工具/产品`、`🧠 有价值的行业洞察或趋势`、`💰 商业机会或变现思路`、`📌 可这周实践的具体行动`、`✍️ 今日最值得写的选题`；各分类条数上限分别为：工具最多 8 条，洞察最多 5 条，商机最多 4 条，行动最多 3 条，选题最多 2 条；没有合适内容就省略该类。",
            "6. 严格依据兴趣画像 focus / recent_context 筛选；ignore 中相关内容一律跳过。",
            "7. `actions` 数组只保留来自 `📌 可这周实践的具体行动` 的条目。",
            "8. 除 `🌐 今日热议话题` 外，其余分类中的每条内容格式固定为单行：`• 名称/要点：一句话说明。— @来源账号 · [原文↗](url)`，不要换行，不要加粗，不要在正文中裸露显示具体 URL 文本。**重要：同一 URL 只能在最相关的一个分类中出现一次，禁止跨分类重复引用同一推文。**",
            "9. `✍️ 今日最值得写的选题` 需要输出 2-3 个适合转成 Article 或 Post 的具体题目，每条格式同样保持单行，明确写出建议角度。",
            "10. 语言风格保持简洁、可信、可执行，避免空泛形容词和重复表述。",
            "",
            "兴趣画像 JSON：",
            json.dumps(interests_payload, ensure_ascii=False, indent=2),
            "",
            "扫描范围元信息 JSON：",
            json.dumps(scan_meta, ensure_ascii=False, indent=2),
            "",
            "扫描结果 JSON：",
            json.dumps(
                {
                    "new_ideas_preview": preview,
                    "successful_accounts": result_payload.get("successful_accounts"),
                    "failed_accounts": result_payload.get("failed_accounts"),
                    "new_items_count": result_payload.get("new_items_count"),
                    "elapsed_str": result_payload.get("elapsed_str"),
                    "preview_count": len(preview),
                },
                ensure_ascii=False,
                indent=2,
            ),
        ]
    )


def _build_radar_weekly_prompt(analysis_payload: dict, actions_payload: dict):
    pending_actions = [
        item for item in actions_payload.get("actions", []) if item.get("status") == "pending"
    ][:5]
    return "\n".join(
        [
            "你是一个严格基于真实 X 分析结果生成中文周报的分析助手。",
            "禁止编造任何链接、账号、产品、数据或观点；只能使用输入 JSON 中真实存在的字段。",
            "请返回 JSON 对象，不要解释，不要代码围栏。",
            "",
            "返回格式：",
            "{",
            '  "markdown": "完整周报 Markdown 文本",',
            '  "actions": [',
            '    {"action":"本周新增行动","source_link":"原文链接","source_account":"@账号"}',
            "  ]",
            "}",
            "",
            "周报要求：",
            "1. 顶部标题为 `📊 X 创意雷达周报 YYYY-MM-DD`。",
            "2. 先输出 `📈 本周热点话题 Top5`：先阅读 `hot_topics.keywords` 全部关键词，再语义聚类成 5 个真实话题簇，禁止直接照抄关键词当话题名。",
            "3. 若 `topic_trend.status == ok`，对应话题后标注 📈 / 📉 / 🆕。",
            "4. 再输出：`🌐 二度人脉推荐`、`💡 本周亮点推文`、`📋 行动追踪`、`🔧 账号调整建议`。",
            "5. `📋 行动追踪` 里包含“上周 pending 行动”和“本周新增行动”。",
            "6. `🔧 账号调整建议` 要给出 `✅ 建议保留` 和 `❌ 建议移除`。",
            "7. `actions` 数组只保留“本周新增行动”的新增项。",
            "",
            "分析结果 JSON：",
            json.dumps(analysis_payload, ensure_ascii=False, indent=2),
            "",
            "已有 pending actions JSON：",
            json.dumps(pending_actions, ensure_ascii=False, indent=2),
        ]
    )


def _backup_file(path: Path):
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.stem}.skeleton.{ts}{path.suffix}")
    shutil.copy2(path, backup_path)
    return backup_path


def _run_python_script(script_path: Path, extra_args):
    cmd = [sys.executable, str(script_path), *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(script_path.parent))


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


def _cmd_generate(args):
    md_path = Path(args.md_path).expanduser().resolve()
    if not md_path.exists():
        _print_json({"ok": False, "error": "Markdown 文件不存在"})
        return 1

    cfg = _resolve_generate_config(args)
    if not cfg.get("llm_chain"):
        _print_json(
            {
                "ok": False,
                "error": "未配置可用 LLM。请设置 XPOST_LLM_API_KEY（及 URL/模型），或完整设置备份变量 XPOST_LLM_FALLBACK_API_URL、XPOST_LLM_FALLBACK_API_KEY、XPOST_LLM_FALLBACK_MODEL。",
            }
        )
        return 1

    raw_markdown = _read_text(md_path)
    try:
        prompt = _build_generation_prompt(md_path, raw_markdown, args.style, args.topic)
    except Exception as exc:
        _print_json({"ok": False, "error": f"生成 Prompt 失败: {exc}"})
        return 1

    start_ts = time.time()
    try:
        generated, llm_meta = _call_llm_with_fallback(
            cfg["llm_chain"],
            prompt,
            args.max_tokens,
            return_debug=False,
        )
    except Exception as exc:
        _print_json({"ok": False, "error": f"LLM 生成失败: {exc}"})
        return 1

    output_path = Path(args.output).expanduser().resolve() if args.output else md_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if output_path == md_path:
        backup_path = _backup_file(md_path)

    _write_text(output_path, generated + ("\n" if not generated.endswith("\n") else ""))
    ok, errors, warnings = _validate_markdown(output_path)
    total_ms = int((time.time() - start_ts) * 1000)

    placeholder_hits = [hint for hint in PLACEHOLDER_HINTS if hint in generated]
    if placeholder_hits:
        warnings.append(
            {
                "code": "W_PLACEHOLDER_LEFT",
                "message": f"生成结果中仍然包含模板占位语句: {', '.join(placeholder_hits)}",
            }
        )

    _print_json(
        {
            "ok": ok and not placeholder_hits,
            "md_path": str(output_path),
            "backup_path": str(backup_path) if backup_path else None,
            "model": cfg["model"],
            "llm_model_effective": llm_meta.get("model"),
            "llm_route": llm_meta.get("route"),
            "api_url": cfg["api_url"],
            "llm_api_url_effective": llm_meta.get("api_url"),
            "generated_chars": len(generated),
            "validate": {
                "ok": ok,
                "errors": errors,
                "warnings": warnings,
            },
            "timings": {
                "total_ms": total_ms,
            },
        }
    )
    return 0 if ok and not placeholder_hits else 1


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


def _cmd_reply(args):
    """回复指定推文"""
    if args.profile_dir:
        os.environ["XPOST_PROFILE_DIR"] = str(Path(args.profile_dir).expanduser().resolve())
    if args.no_wait:
        os.environ["XPOST_NO_WAIT"] = "1"
    if args.remote_debugging_port:
        os.environ["XPOST_REMOTE_DEBUGGING_PORT"] = str(args.remote_debugging_port)
    if args.observe_ms is not None:
        os.environ["XPOST_STEP_PAUSE_MS"] = str(args.observe_ms)

    sys.path.insert(0, str(BASE_DIR))
    try:
        from auto_reply_post import auto_reply_post
    except Exception as exc:
        _print_json({"ok": False, "error": f"Reply 模块加载失败: {exc}"})
        return 1

    start_ts = time.time()
    try:
        success = auto_reply_post(
            url=args.url,
            text=args.text,
            publish=args.publish,
            step_pause_ms=args.observe_ms,
        )
        total_ms = int((time.time() - start_ts) * 1000)
        _print_json(
            {
                "ok": success,
                "mode": "publish" if args.publish else "draft",
                "url": args.url,
                "text_length": len(args.text),
                "timings": {"total_ms": total_ms},
            }
        )
        return 0 if success else 1
    except Exception as exc:
        _print_json({"ok": False, "error": f"回复失败: {exc}"})
        return 1


def _cmd_reply_extract(args):
    """仅提取推文正文"""
    if args.profile_dir:
        os.environ["XPOST_PROFILE_DIR"] = str(Path(args.profile_dir).expanduser().resolve())
    if args.remote_debugging_port:
        os.environ["XPOST_REMOTE_DEBUGGING_PORT"] = str(args.remote_debugging_port)

    sys.path.insert(0, str(BASE_DIR))
    try:
        from auto_reply_post import auto_extract_tweet
    except Exception as exc:
        _print_json({"ok": False, "error": f"Reply 模块加载失败: {exc}"})
        return 1

    start_ts = time.time()
    try:
        data = auto_extract_tweet(url=args.url)
        total_ms = int((time.time() - start_ts) * 1000)
        _print_json(
            {
                "ok": True,
                "url": args.url,
                "handle": data.get("handle", ""),
                "text": data.get("text", ""),
                "lang": data.get("lang", "unknown"),
                "timings": {"total_ms": total_ms},
            }
        )
        return 0
    except Exception as exc:
        _print_json({"ok": False, "error": f"提取失败: {exc}"})
        return 1


def _cmd_radar_scan(_args):
    script_path = XINFO_DIR / "x_ideas_scan.py"
    result_path = XINFO_DIR / "RESULT.json"
    day_result_path = XINFO_DIR / "log" / "day" / f"{time.strftime('%Y-%m-%d')}_result.json"
    if not script_path.exists():
        _print_json({"ok": False, "error": "xinfo 扫描脚本不存在"})
        return 1

    start_ts = time.time()
    proc = _run_python_script(script_path, [])
    total_ms = int((time.time() - start_ts) * 1000)

    parsed = None
    if result_path.exists():
        try:
            parsed = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            parsed = None

    ok = proc.returncode == 0 and (parsed is None or parsed.get("success", True))

    _print_json(
        {
            "ok": ok,
            "command": "radar-scan",
            "result_path": str(result_path),
            "day_result_path": str(day_result_path),
            "result": parsed,
            "stdout_tail": proc.stdout[-1200:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-1200:] if proc.stderr else "",
            "timings": {
                "total_ms": total_ms,
            },
        }
    )
    return 0 if ok else 1


def _cmd_radar_analyze(args):
    script_path = XINFO_DIR / "analyze_network.py"
    if not script_path.exists():
        _print_json({"ok": False, "error": "xinfo 分析脚本不存在"})
        return 1

    cmd_args = []
    if args.days is not None:
        cmd_args.append(str(args.days))
    if not args.text:
        cmd_args.append("--json")

    start_ts = time.time()
    proc = _run_python_script(script_path, cmd_args)
    total_ms = int((time.time() - start_ts) * 1000)

    parsed = None
    if not args.text and proc.stdout:
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            parsed = None

    ok = proc.returncode == 0
    if parsed and isinstance(parsed, dict) and parsed.get("error"):
        ok = False

    _print_json(
        {
            "ok": ok,
            "command": "radar-analyze",
            "json_mode": not args.text,
            "days": args.days,
            "result": parsed,
            "stdout_tail": proc.stdout[-2000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-1200:] if proc.stderr else "",
            "timings": {
                "total_ms": total_ms,
            },
        }
    )
    return 0 if ok else 1


def _cmd_radar_daily(args):
    result_path = Path(args.result_file).expanduser() if args.result_file else XINFO_DIR / "RESULT.json"
    interests_path = Path(args.interests_file).expanduser() if args.interests_file else XINFO_LOG_DIR / "interests.json"
    actions_path = Path(args.actions_file).expanduser() if args.actions_file else XINFO_LOG_DIR / "actions.json"
    output_path = Path(args.output).expanduser() if args.output else XINFO_DAY_DIR / f"{_today_str()}.md"
    runtime_context = {
        "command": "radar-daily",
        "result_path": str(result_path),
        "interests_path": str(interests_path),
        "actions_path": str(actions_path),
        "output_path": str(output_path),
    }

    if not result_path.exists():
        log_path = _record_radar_runtime(
            "radar-daily",
            {
                **runtime_context,
                "ok": False,
                "error": f"扫描结果不存在: {result_path}",
            },
        )
        _print_json({"ok": False, "error": f"扫描结果不存在: {result_path}", "log_path": log_path})
        return 1

    created_support = []
    if _ensure_support_file(interests_path, _default_interests_payload()):
        created_support.append(str(interests_path))
    if _ensure_support_file(actions_path, _default_actions_payload()):
        created_support.append(str(actions_path))

    result_payload = _read_json_file(result_path)
    interests_payload = _read_json_file(interests_path, default=_default_interests_payload())

    llm_cfg = _resolve_radar_llm_config(args)
    runtime_context.update(
        {
            "llm_model": llm_cfg.get("model"),
            "api_url": llm_cfg.get("api_url"),
        }
    )
    if not llm_cfg.get("llm_chain"):
        log_path = _record_radar_runtime(
            "radar-daily",
            {
                **runtime_context,
                "ok": False,
                "error": "未配置可用 LLM。请设置 XPOST_LLM_API_KEY，或完整设置 XPOST_LLM_FALLBACK_API_URL / KEY / MODEL。",
            },
        )
        _print_json(
            {
                "ok": False,
                "error": "未配置可用 LLM。请设置 XPOST_LLM_API_KEY，或完整设置 XPOST_LLM_FALLBACK_API_URL / KEY / MODEL。",
                "log_path": log_path,
            }
        )
        return 1

    summary = result_payload.get("summary", {})
    status = summary.get("status")
    preview = summary.get("new_ideas_preview", [])

    # ── 过滤非当天推文，减少 LLM token 消耗 ──────────────────────
    # RSS pub_date 格式为 RFC 2822: "Wed, 29 Mar 2026 21:29:31 GMT"
    # 新增账号首次扫描会涌入大量历史推文，这里只保留当天的
    from email.utils import parsedate_to_datetime as _parse_rfc2822
    _today_str_val = datetime.now().strftime("%Y-%m-%d")
    _today_preview = []
    _skipped_old = 0
    for _item in preview:
        try:
            _dt = _parse_rfc2822(_item.get("time", ""))
            if _dt.strftime("%Y-%m-%d") == _today_str_val:
                _today_preview.append(_item)
            else:
                _skipped_old += 1
        except Exception:
            _today_preview.append(_item)  # 解析失败的保留，不丢数据
    if _today_preview:
        preview = _today_preview
        if _skipped_old:
            print(f"  📅 日报过滤: 保留当天 {len(preview)} 条, 跳过历史 {_skipped_old} 条")
    # 过滤后为空则保留原始 preview（兜底：首次使用/跨天场景）
    # ── 过滤结束 ──────────────────────────────────────────────

    # 限制 preview 条数，避免 prompt 超出 LLM 输出 token 上限
    max_preview = getattr(args, 'max_preview', 300)
    if len(preview) > max_preview:
        import random
        preview = random.sample(preview, max_preview)
    # 将过滤/采样后的 preview 写回 result_payload，确保 prompt 使用干净数据
    result_payload = dict(result_payload)
    result_payload["summary"] = dict(summary)
    result_payload["summary"]["new_ideas_preview"] = preview
    result_payload["summary"]["sampled_preview_count"] = len(preview)
    if status == "no_new" or not preview:
        body = "\n".join(
            [
                f"📅 {datetime.now().year}年{datetime.now().month}月{datetime.now().day}日",
                "",
                "📭 今日暂无新推文",
            ]
        )
        report_json = {"markdown": body, "actions": []}
        attempt_logs = []
        llm_used = None
    else:
        try:
            prompt = _build_radar_daily_prompt(result_payload, interests_payload)
            report_json, attempt_logs, llm_used = _generate_radar_report(
                prompt, llm_cfg["llm_chain"], args.max_tokens
            )
        except Exception as exc:
            log_path = _record_radar_runtime(
                "radar-daily",
                {
                    **runtime_context,
                    "ok": False,
                    "error": f"Radar 日报生成失败: {exc}",
                    "attempts": getattr(exc, "attempt_logs", []),
                },
            )
            _print_json({"ok": False, "error": f"Radar 日报生成失败: {exc}", "log_path": log_path})
            return 1

    markdown_body = (report_json.get("markdown") or "").strip()
    extracted_markdown = _extract_markdown_from_text(markdown_body)
    if extracted_markdown:
        markdown_body = extracted_markdown
    if not markdown_body:
        log_path = _record_radar_runtime(
            "radar-daily",
            {
                **runtime_context,
                "ok": False,
                "error": "Radar 日报生成失败：LLM 未返回 markdown",
                "attempts": attempt_logs,
            },
        )
        _print_json({"ok": False, "error": "Radar 日报生成失败：LLM 未返回 markdown", "log_path": log_path})
        return 1

    eff_model = (llm_used or {}).get("model") or llm_cfg["model"]
    eff_route = (llm_used or {}).get("route")

    added_actions = _append_actions(actions_path, report_json.get("actions", []))
    daily_meta = {
        "report_type": "radar_daily",
        "generated_at": _now_str(),
        "llm_model": eff_model,
        "source_result_file": str(result_path),
    }
    if eff_route:
        daily_meta["llm_route"] = eff_route
    report_text = _wrap_report_markdown(markdown_body, daily_meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    log_path = _record_radar_runtime(
        "radar-daily",
        {
            **runtime_context,
            "ok": True,
            "actions_added": added_actions,
            "attempts": attempt_logs,
            "llm_route": eff_route,
            "llm_model_effective": eff_model,
        },
    )

    _print_json(
        {
            "ok": True,
            "command": "radar-daily",
            "output_path": str(output_path),
            "actions_path": str(actions_path),
            "actions_added": added_actions,
            "llm_model": eff_model,
            "llm_route": eff_route,
            "created_support_files": created_support,
            "log_path": log_path,
        }
    )
    return 0


def _cmd_radar_weekly(args):
    analysis_path = Path(args.analysis_file).expanduser() if args.analysis_file else XINFO_DAY_DIR / f"{_today_str()}_analysis.json"
    actions_path = Path(args.actions_file).expanduser() if args.actions_file else XINFO_LOG_DIR / "actions.json"
    output_path = Path(args.output).expanduser() if args.output else XINFO_WEEK_DIR / f"{_today_str()}.md"
    runtime_context = {
        "command": "radar-weekly",
        "analysis_path": str(analysis_path),
        "actions_path": str(actions_path),
        "output_path": str(output_path),
    }

    if not analysis_path.exists():
        log_path = _record_radar_runtime(
            "radar-weekly",
            {
                **runtime_context,
                "ok": False,
                "error": f"分析结果不存在: {analysis_path}",
            },
        )
        _print_json({"ok": False, "error": f"分析结果不存在: {analysis_path}", "log_path": log_path})
        return 1

    created_support = []
    if _ensure_support_file(actions_path, _default_actions_payload()):
        created_support.append(str(actions_path))

    analysis_payload = _read_json_file(analysis_path)
    actions_payload = _read_json_file(actions_path, default=_default_actions_payload())

    llm_cfg = _resolve_radar_llm_config(args)
    runtime_context.update(
        {
            "llm_model": llm_cfg.get("model"),
            "api_url": llm_cfg.get("api_url"),
        }
    )
    if not llm_cfg.get("llm_chain"):
        log_path = _record_radar_runtime(
            "radar-weekly",
            {
                **runtime_context,
                "ok": False,
                "error": "未配置可用 LLM。请设置 XPOST_LLM_API_KEY，或完整设置 XPOST_LLM_FALLBACK_API_URL / KEY / MODEL。",
            },
        )
        _print_json(
            {
                "ok": False,
                "error": "未配置可用 LLM。请设置 XPOST_LLM_API_KEY，或完整设置 XPOST_LLM_FALLBACK_API_URL / KEY / MODEL。",
                "log_path": log_path,
            }
        )
        return 1

    try:
        prompt = _build_radar_weekly_prompt(analysis_payload, actions_payload)
        report_json, attempt_logs, llm_used = _generate_radar_report(
            prompt, llm_cfg["llm_chain"], args.max_tokens
        )
    except Exception as exc:
        log_path = _record_radar_runtime(
            "radar-weekly",
            {
                **runtime_context,
                "ok": False,
                "error": f"Radar 周报生成失败: {exc}",
                "attempts": getattr(exc, "attempt_logs", []),
            },
        )
        _print_json({"ok": False, "error": f"Radar 周报生成失败: {exc}", "log_path": log_path})
        return 1

    markdown_body = (report_json.get("markdown") or "").strip()
    extracted_markdown = _extract_markdown_from_text(markdown_body)
    if extracted_markdown:
        markdown_body = extracted_markdown
    if not markdown_body:
        log_path = _record_radar_runtime(
            "radar-weekly",
            {
                **runtime_context,
                "ok": False,
                "error": "Radar 周报生成失败：LLM 未返回 markdown",
                "attempts": attempt_logs,
            },
        )
        _print_json({"ok": False, "error": "Radar 周报生成失败：LLM 未返回 markdown", "log_path": log_path})
        return 1

    eff_model = (llm_used or {}).get("model") or llm_cfg["model"]
    eff_route = (llm_used or {}).get("route")

    added_actions = _append_actions(actions_path, report_json.get("actions", []))
    weekly_meta = {
        "report_type": "radar_weekly",
        "generated_at": _now_str(),
        "llm_model": eff_model,
        "source_analysis_file": str(analysis_path),
        "scope_days": analysis_payload.get("scope_days", 7),
    }
    if eff_route:
        weekly_meta["llm_route"] = eff_route
    report_text = _wrap_report_markdown(markdown_body, weekly_meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    log_path = _record_radar_runtime(
        "radar-weekly",
        {
            **runtime_context,
            "ok": True,
            "actions_added": added_actions,
            "attempts": attempt_logs,
            "llm_route": eff_route,
            "llm_model_effective": eff_model,
        },
    )

    _print_json(
        {
            "ok": True,
            "command": "radar-weekly",
            "output_path": str(output_path),
            "actions_path": str(actions_path),
            "actions_added": added_actions,
            "llm_model": eff_model,
            "llm_route": eff_route,
            "created_support_files": created_support,
            "log_path": log_path,
        }
    )
    return 0


def _cmd_radar_accounts(args):
    script_path = XINFO_DIR / "manage_accounts.py"
    if not script_path.exists():
        _print_json({"ok": False, "error": "xinfo 账号管理脚本不存在"})
        return 1

    if args.action in {"add", "remove", "restore"} and not args.username:
        _print_json({"ok": False, "error": f"radar-accounts {args.action} 需要 username"})
        return 1
    if args.action == "add" and not args.note:
        _print_json({"ok": False, "error": "radar-accounts add 需要 note"})
        return 1

    cmd_args = [args.action]
    if args.username:
        cmd_args.append(args.username)
    if args.note:
        cmd_args.append(args.note)

    proc = _run_python_script(script_path, cmd_args)
    _print_json(
        {
            "ok": proc.returncode == 0,
            "command": "radar-accounts",
            "action": args.action,
            "username": args.username,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    )
    return 0 if proc.returncode == 0 else 1


def _cmd_follower_stats(args):
    """采集 X 粉丝数据（使用 patchright 浏览器）"""
    script_path = BASE_DIR / "fetch_follower_stats.py"
    if not script_path.exists():
        _print_json({"ok": False, "error": "fetch_follower_stats.py 脚本不存在"})
        return 1

    username = args.username or os.environ.get("XPOST_USERNAME", "jackaiwison")
    cmd_args = [username, "--json-only", "--headless"]
    if args.timeout:
        cmd_args.extend(["--timeout", str(args.timeout)])

    proc = _run_python_script(script_path, cmd_args)

    # 解析 stdout JSON
    try:
        result = json.loads(proc.stdout)
    except Exception:
        result = {
            "ok": False,
            "error": "解析输出失败",
            "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
        }

    _print_json(result)
    return 0 if result.get("ok") else 1


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


def _cmd_scheduler(args):
    """管理 launchd 定时任务调度器"""
    action = args.action
    plist_template = BASE_DIR / "scripts" / "com.gitxpost.daily.plist"
    plist_target = Path.home() / "Library" / "LaunchAgents" / "com.gitxpost.daily.plist"
    scheduler_script = BASE_DIR / "scripts" / "daily_scheduler.sh"
    label = "com.gitxpost.daily"

    if action == "install":
        # 解析时间参数
        time_str = args.time or "09:00"
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except Exception:
            _print_json({"ok": False, "error": f"时间格式错误，应为 HH:MM (00:00-23:59)，收到: {time_str}"})
            return 1

        # 检查脚本是否存在
        if not scheduler_script.exists():
            _print_json({"ok": False, "error": f"调度脚本不存在: {scheduler_script}"})
            return 1

        # 读取模板并替换占位符
        if not plist_template.exists():
            _print_json({"ok": False, "error": f"plist 模板不存在: {plist_template}"})
            return 1

        plist_content = plist_template.read_text(encoding="utf-8")
        plist_content = plist_content.replace("{HOUR}", str(hour))
        plist_content = plist_content.replace("{MINUTE}", str(minute))

        # 如果已安装，先卸载
        if plist_target.exists():
            subprocess.run(["launchctl", "unload", str(plist_target)], capture_output=True)

        # 写入 plist
        plist_target.parent.mkdir(parents=True, exist_ok=True)
        plist_target.write_text(plist_content, encoding="utf-8")

        # 加载到 launchd
        proc = subprocess.run(["launchctl", "load", str(plist_target)], capture_output=True, text=True)
        if proc.returncode != 0:
            _print_json({
                "ok": False,
                "error": "launchctl load 失败",
                "stderr": proc.stderr.strip(),
            })
            return 1

        _print_json({
            "ok": True,
            "action": "install",
            "scheduled_time": time_str,
            "plist_path": str(plist_target),
            "message": f"调度器已安装，将在每天 {time_str} 执行",
        })
        return 0

    elif action == "uninstall":
        if not plist_target.exists():
            _print_json({
                "ok": True,
                "action": "uninstall",
                "message": "调度器未安装",
            })
            return 0

        # 卸载
        proc = subprocess.run(["launchctl", "unload", str(plist_target)], capture_output=True, text=True)
        plist_target.unlink()

        _print_json({
            "ok": True,
            "action": "uninstall",
            "message": "调度器已卸载",
        })
        return 0

    elif action == "status":
        # 检查 plist 是否存在
        installed = plist_target.exists()
        scheduled_time = None
        next_run = None

        if installed:
            # 解析 plist 获取时间
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(plist_target)
                root = tree.getroot()
                plist_dict = root.find("dict")
                keys = list(plist_dict.iter("key"))
                for i, key in enumerate(keys):
                    if key.text == "StartCalendarInterval":
                        interval_dict = list(plist_dict)[i + 1]
                        hour_elem = None
                        minute_elem = None
                        for j, k in enumerate(interval_dict.iter("key")):
                            if k.text == "Hour":
                                hour_elem = list(interval_dict)[j + 1]
                            elif k.text == "Minute":
                                minute_elem = list(interval_dict)[j + 1]
                        if hour_elem is not None and minute_elem is not None:
                            hour = int(hour_elem.text)
                            minute = int(minute_elem.text)
                            scheduled_time = f"{hour:02d}:{minute:02d}"
                            
                            # 计算下次执行时间
                            now = datetime.now()
                            next_run_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            if next_run_dt <= now:
                                next_run_dt = next_run_dt.replace(day=now.day + 1)
                            next_run = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        # 检查最近执行日志
        last_run = None
        log_dir = XINFO_RUNTIME_DIR
        if log_dir.exists():
            log_files = sorted(log_dir.glob("scheduler_*.log"), reverse=True)
            if log_files:
                latest_log = log_files[0]
                try:
                    lines = latest_log.read_text(encoding="utf-8").splitlines()
                    for line in lines:
                        if line.startswith("==========") and "DONE" in line:
                            # 提取时间戳
                            match = re.search(r"DONE (.+?) =", line)
                            if match:
                                last_run = match.group(1).strip()
                                break
                except Exception:
                    pass

        _print_json({
            "ok": True,
            "action": "status",
            "installed": installed,
            "scheduled_time": scheduled_time,
            "next_run": next_run,
            "last_run": last_run,
            "plist_path": str(plist_target) if installed else None,
        })
        return 0

    elif action == "run-now":
        if not scheduler_script.exists():
            _print_json({"ok": False, "error": f"调度脚本不存在: {scheduler_script}"})
            return 1

        # 直接执行脚本
        start_ts = time.time()
        proc = subprocess.run(["/bin/bash", str(scheduler_script)], capture_output=True, text=True, cwd=str(BASE_DIR))
        total_ms = int((time.time() - start_ts) * 1000)

        _print_json({
            "ok": proc.returncode == 0,
            "action": "run-now",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-1000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-1000:] if proc.stderr else "",
            "timings": {"total_ms": total_ms},
        })
        return 0 if proc.returncode == 0 else 1

    elif action == "logs":
        lines_limit = args.lines or 50
        log_dir = XINFO_RUNTIME_DIR
        
        if not log_dir.exists():
            _print_json({
                "ok": True,
                "action": "logs",
                "logs": [],
                "message": "日志目录不存在",
            })
            return 0

        log_files = sorted(log_dir.glob("scheduler_*.log"), reverse=True)
        if not log_files:
            _print_json({
                "ok": True,
                "action": "logs",
                "logs": [],
                "message": "暂无日志",
            })
            return 0

        # 读取最新日志文件
        latest_log = log_files[0]
        try:
            content = latest_log.read_text(encoding="utf-8")
            lines = content.splitlines()
            recent_lines = lines[-lines_limit:] if len(lines) > lines_limit else lines
            
            _print_json({
                "ok": True,
                "action": "logs",
                "log_file": latest_log.name,
                "total_lines": len(lines),
                "returned_lines": len(recent_lines),
                "logs": recent_lines,
            })
            return 0
        except Exception as exc:
            _print_json({
                "ok": False,
                "action": "logs",
                "error": f"读取日志失败: {exc}",
            })
            return 1

    else:
        _print_json({"ok": False, "error": f"未知操作: {action}"})
        return 1


def _cmd_queue_processor(args):
    """管理发布队列处理器"""
    action = args.action
    plist_template = BASE_DIR / "scripts" / "com.gitxpost.queue.plist"
    plist_target = Path.home() / "Library" / "LaunchAgents" / "com.gitxpost.queue.plist"
    processor_script = BASE_DIR / "scripts" / "process_publish_queue.py"
    label = "com.gitxpost.queue"
    log_dir = XINFO_RUNTIME_DIR

    if action == "install":
        # 检查脚本是否存在
        if not processor_script.exists():
            _print_json({"ok": False, "error": f"处理器脚本不存在: {processor_script}"})
            return 1

        # 读取模板并替换占位符
        if not plist_template.exists():
            _print_json({"ok": False, "error": f"plist 模板不存在: {plist_template}"})
            return 1

        plist_content = plist_template.read_text(encoding="utf-8")
        plist_content = plist_content.replace("VENV_PYTHON_PATH", sys.executable)
        plist_content = plist_content.replace("SCRIPT_PATH", str(processor_script))
        plist_content = plist_content.replace("BASE_DIR", str(BASE_DIR))
        plist_content = plist_content.replace("LOG_DIR", str(log_dir))

        # 如果已安装，先卸载
        if plist_target.exists():
            subprocess.run(["launchctl", "unload", str(plist_target)], capture_output=True)

        # 写入 plist
        plist_target.parent.mkdir(parents=True, exist_ok=True)
        plist_target.write_text(plist_content, encoding="utf-8")

        # 加载到 launchd
        proc = subprocess.run(["launchctl", "load", str(plist_target)], capture_output=True, text=True)
        if proc.returncode != 0:
            _print_json({
                "ok": False,
                "error": "launchctl load 失败",
                "stderr": proc.stderr.strip(),
            })
            return 1

        _print_json({
            "ok": True,
            "action": "install",
            "plist_path": str(plist_target),
            "message": "队列处理器已安装，将每 5 分钟检查一次队列",
        })
        return 0

    elif action == "uninstall":
        if not plist_target.exists():
            _print_json({
                "ok": True,
                "action": "uninstall",
                "message": "队列处理器未安装",
            })
            return 0

        # 卸载
        proc = subprocess.run(["launchctl", "unload", str(plist_target)], capture_output=True, text=True)
        plist_target.unlink()

        _print_json({
            "ok": True,
            "action": "uninstall",
            "message": "队列处理器已卸载",
        })
        return 0

    elif action == "status":
        # 检查 plist 是否存在
        installed = plist_target.exists()
        
        # 检查 launchd 状态
        running = False
        if installed:
            proc = subprocess.run(
                ["launchctl", "list", label],
                capture_output=True,
                text=True
            )
            running = proc.returncode == 0

        _print_json({
            "ok": True,
            "action": "status",
            "installed": installed,
            "running": running,
            "interval": "5 minutes",
            "plist_path": str(plist_target) if installed else None,
        })
        return 0

    elif action == "run-now":
        # 检查脚本是否存在
        if not processor_script.exists():
            _print_json({"ok": False, "error": f"处理器脚本不存在: {processor_script}"})
            return 1

        # 直接执行脚本
        start_ts = time.time()
        proc = subprocess.run(
            [sys.executable, str(processor_script)],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR)
        )
        total_ms = int((time.time() - start_ts) * 1000)

        _print_json({
            "ok": proc.returncode == 0,
            "action": "run-now",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr if proc.stderr else None,
            "timings": {"total_ms": total_ms},
        })
        return 0 if proc.returncode == 0 else 1

    else:
        _print_json({"ok": False, "error": f"未知操作: {action}"})
        return 1


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

    p_generate = sub.add_parser("generate", help="Generate a full article from markdown skeleton")
    p_generate.add_argument("md_path", help="Markdown skeleton path")
    p_generate.add_argument("--output", help="Optional output path (default: overwrite md_path)")
    p_generate.add_argument("--style", choices=sorted(STYLE_PROMPTS.keys()), help="Prompt style override")
    p_generate.add_argument("--topic", help="Topic override for LLM prompt")
    p_generate.add_argument("--model", help="LLM model override")
    p_generate.add_argument("--api-url", help="LLM messages API URL override")
    p_generate.add_argument("--max-tokens", type=int, default=9000, help="LLM max tokens for generation")
    p_generate.set_defaults(func=_cmd_generate)

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

    p_reply = sub.add_parser("reply", help="Reply to a tweet")
    p_reply.add_argument("url", help="Tweet URL to reply to")
    p_reply.add_argument("text", help="Reply text content (max 280 characters)")
    p_reply.add_argument("--publish", action="store_true", help="Send reply (default: draft / fill only)")
    p_reply.add_argument("--profile-dir", help="Chrome profile directory")
    p_reply.add_argument("--no-wait", action="store_true", help="Do not wait after completion")
    p_reply.add_argument("--remote-debugging-port", type=int, help="Chrome CDP port override")
    p_reply.add_argument("--observe-ms", type=int, default=900, help="Pause after key steps so the UI is visible")
    p_reply.set_defaults(func=_cmd_reply)

    p_reply_extract = sub.add_parser("reply-extract", help="Extract tweet text without replying")
    p_reply_extract.add_argument("url", help="Tweet URL to extract")
    p_reply_extract.add_argument("--profile-dir", help="Chrome profile directory")
    p_reply_extract.add_argument("--remote-debugging-port", type=int, help="Chrome CDP port override")
    p_reply_extract.set_defaults(func=_cmd_reply_extract)

    p_radar_scan = sub.add_parser("radar-scan", help="Run X radar scan")
    p_radar_scan.set_defaults(func=_cmd_radar_scan)

    p_radar_analyze = sub.add_parser("radar-analyze", help="Run X radar analysis")
    p_radar_analyze.add_argument("--days", type=int, help="Only analyze recent N days")
    p_radar_analyze.add_argument("--text", action="store_true", help="Return human-readable text instead of JSON")
    p_radar_analyze.set_defaults(func=_cmd_radar_analyze)

    p_radar_daily = sub.add_parser("radar-daily", help="Generate X radar daily markdown report")
    p_radar_daily.add_argument("--result-file", help="Scan result JSON path (default: xinfo/RESULT.json)")
    p_radar_daily.add_argument("--interests-file", help="Interests JSON path (default: xinfo/log/interests.json)")
    p_radar_daily.add_argument("--actions-file", help="Actions JSON path (default: xinfo/log/actions.json)")
    p_radar_daily.add_argument("--output", help="Output markdown path (default: xinfo/log/day/YYYY-MM-DD.md)")
    p_radar_daily.add_argument("--model", help="LLM model override (default: claude-opus-4-6)")
    p_radar_daily.add_argument("--api-url", help="LLM messages API URL override")
    p_radar_daily.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_RADAR_DAILY_MAX_TOKENS,
        help=f"LLM max tokens for daily report (default: {DEFAULT_RADAR_DAILY_MAX_TOKENS}; fallback 链路另受 XPOST_LLM_FALLBACK_MAX_TOKENS 上限)",
    )
    p_radar_daily.add_argument("--max-preview", type=int, default=200, help="Max preview tweets to include in prompt (default: 100)")
    p_radar_daily.set_defaults(func=_cmd_radar_daily)

    p_radar_weekly = sub.add_parser("radar-weekly", help="Generate X radar weekly markdown report")
    p_radar_weekly.add_argument("--analysis-file", help="Analysis JSON path (default: xinfo/log/day/YYYY-MM-DD_analysis.json)")
    p_radar_weekly.add_argument("--actions-file", help="Actions JSON path (default: xinfo/log/actions.json)")
    p_radar_weekly.add_argument("--output", help="Output markdown path (default: xinfo/log/week/YYYY-MM-DD.md)")
    p_radar_weekly.add_argument("--model", help="LLM model override (default: claude-opus-4-6)")
    p_radar_weekly.add_argument("--api-url", help="LLM messages API URL override")
    p_radar_weekly.add_argument("--max-tokens", type=int, default=9000, help="LLM max tokens for weekly report")
    p_radar_weekly.set_defaults(func=_cmd_radar_weekly)

    p_radar_accounts = sub.add_parser("radar-accounts", help="Manage X radar accounts")
    p_radar_accounts.add_argument("action", choices=["list", "add", "remove", "restore"], help="Account action")
    p_radar_accounts.add_argument("username", nargs="?", help="Account username")
    p_radar_accounts.add_argument("note", nargs="?", help="Optional note for add")
    p_radar_accounts.set_defaults(func=_cmd_radar_accounts)

    p_follower = sub.add_parser("follower-stats", help="Fetch X follower/following counts")
    p_follower.add_argument("username", nargs="?", help="X username (default: jackaiwison)")
    p_follower.add_argument("--timeout", type=int, default=30, help="Page load timeout in seconds")
    p_follower.set_defaults(func=_cmd_follower_stats)

    p_scheduler = sub.add_parser("scheduler", help="Manage launchd daily task scheduler")
    p_scheduler.add_argument("action", choices=["install", "uninstall", "status", "run-now", "logs"], help="Scheduler action")
    p_scheduler.add_argument("--time", help="Scheduled time in HH:MM format (default: 09:00, only for install)")
    p_scheduler.add_argument("--lines", type=int, default=50, help="Number of log lines to show (only for logs)")
    p_scheduler.set_defaults(func=_cmd_scheduler)

    p_queue = sub.add_parser("queue-processor", help="Manage publish queue processor")
    p_queue.add_argument("action", choices=["install", "uninstall", "status", "run-now"], help="Queue processor action")
    p_queue.set_defaults(func=_cmd_queue_processor)

    p_doctor = sub.add_parser("doctor", help="Check environment and deps")
    p_doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
