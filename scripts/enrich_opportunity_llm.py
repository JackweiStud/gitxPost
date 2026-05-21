#!/usr/bin/env python3
"""
Use the configured gitxPost LLM to explain one daily opportunity.

Input: one opportunity JSON object on stdin.
Output: strict JSON with trafficMotif, myAngle, recommendedAction, draftPrompts.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is available in the project venv.
    load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(Path.cwd() / ".env")

MAX_TOKENS = 1600


def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r"^```[\w]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def _infer_llm_kind(api_url: str) -> str:
    value = (api_url or "").lower()
    if "/messages" in value or "anthropic" in value:
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


def _effective_max_tokens_for_spec(spec: dict, max_tokens: int) -> int:
    if spec.get("label") != "fallback":
        return max_tokens
    raw = os.getenv("XPOST_LLM_FALLBACK_MAX_TOKENS", "8192")
    try:
        cap = int(raw)
    except ValueError:
        cap = 8192
    return min(max_tokens, max(1, cap))


def _build_llm_chain() -> list[dict]:
    chain = []
    primary_key = os.getenv("XPOST_LLM_API_KEY")
    primary_url = os.getenv("XPOST_LLM_API_URL", "")
    primary_model = os.getenv("XPOST_LLM_MODEL", "claude-opus-4-6")
    if primary_key and primary_url and primary_model:
        chain.append(
            {
                "label": "primary",
                "api_url": primary_url,
                "api_key": primary_key,
                "model": primary_model,
                "kind": _infer_llm_kind(primary_url),
            }
        )

    fallback_url = os.getenv("XPOST_LLM_FALLBACK_API_URL")
    fallback_key = os.getenv("XPOST_LLM_FALLBACK_API_KEY")
    fallback_model = os.getenv("XPOST_LLM_FALLBACK_MODEL")
    if fallback_url and fallback_key and fallback_model:
        chain.append(
            {
                "label": "fallback",
                "api_url": fallback_url,
                "api_key": fallback_key,
                "model": fallback_model,
                "kind": (os.getenv("XPOST_LLM_FALLBACK_API_KIND") or "openai").strip().lower(),
            }
        )
    return chain


def _call_llm_once(spec: dict, prompt: str) -> str:
    kind = (spec.get("kind") or _infer_llm_kind(spec.get("api_url", ""))).lower()
    max_tokens = _effective_max_tokens_for_spec(spec, MAX_TOKENS)
    payload = {
        "model": spec["model"],
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "messages": [{"role": "user", "content": prompt}],
    }

    if kind == "anthropic":
        url = spec["api_url"].rstrip("/")
        if url.endswith("/v1"):
            url = f"{url}/messages"
        elif not url.endswith("/messages"):
            url = f"{url}/v1/messages"
    else:
        url = _openai_chat_completions_url(spec["api_url"])

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", "gitxPost daily-opportunities")
    if kind == "anthropic":
        request.add_header("x-api-key", spec["api_key"])
        request.add_header("anthropic-version", "2023-06-01")
    else:
        request.add_header("Authorization", f"Bearer {spec['api_key']}")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc

    data = json.loads(raw)
    if kind == "anthropic":
        if data.get("type") != "message":
            error = data.get("error", {}).get("message") or json.dumps(data)[:300]
            raise RuntimeError(f"LLM returned error: {error}")
        parts = [item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"]
        text = "\n".join(parts).strip()
    else:
        error = data.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise RuntimeError(f"LLM returned error: {message}")
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"LLM returned no choices: {json.dumps(data)[:300]}")
        content = (choices[0].get("message") or {}).get("content", "")
        if isinstance(content, list):
            text = "\n".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
        else:
            text = str(content or "").strip()

    if not text:
        raise RuntimeError("LLM returned empty text")
    return text


def _parse_json_response(text: str) -> dict:
    cleaned = _strip_markdown_fences(text)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start < 0 or end <= 0:
        raise ValueError(f"No JSON object in LLM response: {cleaned[:200]}")
    return json.loads(cleaned[start:end])


def _normalize_result(value: dict) -> dict:
    prompts = value.get("draftPrompts") if isinstance(value.get("draftPrompts"), dict) else {}
    return {
        "trafficMotif": str(value.get("trafficMotif") or "").strip(),
        "myAngle": str(value.get("myAngle") or "").strip(),
        "recommendedAction": str(value.get("recommendedAction") or "").strip(),
        "draftPrompts": {
            "standalonePost": str(prompts.get("standalonePost") or "").strip(),
            "reply": str(prompts.get("reply") or "").strip(),
            "quotePost": str(prompts.get("quotePost") or "").strip(),
        },
    }


def _validate_result(value: dict) -> dict:
    normalized = _normalize_result(value)
    missing = []
    for key in ("trafficMotif", "myAngle", "recommendedAction"):
        if not normalized[key]:
            missing.append(key)
    for key in ("standalonePost", "reply", "quotePost"):
        if not normalized["draftPrompts"][key]:
            missing.append(f"draftPrompts.{key}")
    if missing:
        raise ValueError("LLM JSON missing fields: " + ", ".join(missing))
    return normalized


def build_prompt(opportunity: dict) -> str:
    compact = {
        "account": opportunity.get("account"),
        "title": opportunity.get("title"),
        "url": opportunity.get("url"),
        "actionType": opportunity.get("actionType"),
        "finalScore": opportunity.get("finalScore"),
        "metrics": opportunity.get("metrics"),
        "scoreBreakdown": opportunity.get("scoreBreakdown"),
        "tweetText": (opportunity.get("tweetText") or "")[:1800],
    }
    return f"""你是一个增长型个人创作者的 X 内容策略助手。你要基于单条候选推文，判断它的流量母题，并给出作者应该如何借势创作。

输入 opportunity:
{json.dumps(compact, ensure_ascii=False, indent=2)}

只输出 JSON，不要 markdown，不要解释。字段必须完全如下：
{{
  "trafficMotif": "这条内容能获得讨论/传播的核心流量母题，20字以内",
  "myAngle": "结合个人创作者/工程实践可以切入的独特角度，必须具体，不要复述原帖",
  "recommendedAction": "write_standalone_post | reply_with_builder_angle | quote_or_reply_with_specific_take | watch_or_skip 之一",
  "draftPrompts": {{
    "standalonePost": "给后续 LLM 生成独立帖的中文 prompt，包含原帖作者、母题、你的切入角度和写作约束",
    "reply": "给后续 LLM 生成回复的中文 prompt，要求 280 字内、具体、有 builder 视角",
    "quotePost": "给后续 LLM 生成引用帖的中文 prompt，要求一句明确立场 + 2-3 个具体理由"
  }}
}}

要求：
1. 不要硬套 Karpathy/Cursor/Gemini 等固定分类，必须根据输入内容判断。
2. myAngle 要能帮助作者涨粉：有立场、有经验感、有差异化。
3. 不要输出“很棒/认同/值得关注”这种废话。
4. recommendedAction 必须结合 actionType 和指标，不要机械照抄。
"""


def call_llm(prompt: str) -> dict:
    chain = _build_llm_chain()
    if not chain:
        raise RuntimeError(
            "未配置可用 LLM：请设置 XPOST_LLM_API_KEY（及 URL/模型），或完整设置 XPOST_LLM_FALLBACK_API_URL、XPOST_LLM_FALLBACK_API_KEY、XPOST_LLM_FALLBACK_MODEL"
        )
    errors = []
    for spec in chain:
        try:
            text = _call_llm_once(spec, prompt)
            return _validate_result(_parse_json_response(text))
        except Exception as exc:
            errors.append(f"{spec.get('label') or '?'}: {exc}")
    raise RuntimeError("所有 LLM 端点均失败: " + " | ".join(errors))


def main() -> int:
    try:
        opportunity = json.loads(sys.stdin.read())
        result = call_llm(build_prompt(opportunity))
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
