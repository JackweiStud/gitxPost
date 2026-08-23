#!/usr/bin/env python3
"""
读取推文内容，调用 gitxPost .env 里的 LLM，生成 3 条回复备选。
用法: python generate_replies.py "<tweet_text>" "<handle>"

输出 JSON:
  {"A": "...", "B": "...", "C": "...",
   "llm_route": "primary|fallback",
   "llm_model": "<实际模型>",
   "llm_api_url": "<实际 API URL>"}
主 LLM 失败时自动尝试 XPOST_LLM_FALLBACK_*（与 xpost 一致）。
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# scripts/ → x-reply-assistV2 → skills → 仓库根（gitxPost）
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[2]
load_dotenv(_REPO_ROOT / ".env")
# API 子进程 cwd 常为仓库根，再加载一次以兜底路径差异
load_dotenv(Path.cwd() / ".env")

REPLY_MAX_TOKENS = 1024


def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r"^```[\w]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def _infer_llm_kind(api_url: str) -> str:
    u = (api_url or "").lower()
    if "/messages" in u or "anthropic" in u:
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
    cap = max(1, cap)
    return min(max_tokens, cap)


def _build_reply_llm_chain():
    chain = []
    pk = os.getenv("XPOST_LLM_API_KEY")
    pu = os.getenv("XPOST_LLM_API_URL", "")
    pm = os.getenv("XPOST_LLM_MODEL", "claude-opus-4-6")
    if pk and pu and pm:
        chain.append(
            {
                "label": "primary",
                "api_url": pu,
                "api_key": pk,
                "model": pm,
                "kind": _infer_llm_kind(pu),
            }
        )
    fb_u = os.getenv("XPOST_LLM_FALLBACK_API_URL")
    fb_k = os.getenv("XPOST_LLM_FALLBACK_API_KEY")
    fb_m = os.getenv("XPOST_LLM_FALLBACK_MODEL")
    if fb_u and fb_k and fb_m:
        fb_kind = (os.getenv("XPOST_LLM_FALLBACK_API_KIND") or "openai").strip().lower()
        chain.append(
            {
                "label": "fallback",
                "api_url": fb_u,
                "api_key": fb_k,
                "model": fb_m,
                "kind": fb_kind,
            }
        )
    return chain


def build_prompt(tweet_text: str, handle: str) -> str:
    return f"""Write 3 reply options for this tweet. You are a real person — a builder who ships code, not a commentator.

Tweet by {handle}:
{tweet_text}

RULES:
1. Output ONLY valid JSON, nothing else
2. Each reply ≤ 280 characters. Shorter is better
3. Match the tweet's language (Chinese tweet → Chinese reply, English → English)
4. If English: use plain, short words. Write like texting a coworker, not writing an essay
5. Format:
{{"A": "ask a specific follow-up question", "B": "share a concrete personal experience or trick", "C": "short punchy agreement (1-2 sentences max)"}}

BANNED phrases — never use any of these:
- "Great insight" / "Great point" / "Love this" / "This resonates"
- "I couldn't agree more" / "So true" / "Well said"
- "game-changer" / "fascinating" / "incredible" / "amazing"
- "This is exactly what..." / "As someone who..."
- "Thanks for sharing" / "Thank you for..."
- Any sentence starting with "I think" or "I believe"
- "深有同感" / "说得太好了" / "非常认同" / "受益匪浅"

GOOD reply examples (for tone reference only, don't copy):
- "we ran into this exact thing last week. ended up just caching the embeddings locally — cut latency by 80%"
- "wait does this work with streaming responses too? been stuck on that for days"
- "the token cost part is real. our bill 3x'd after we stopped being lazy about prompts"
- "这个思路我们试过，坑在 context window 不够长的时候会丢关键信息"
- "好奇你们用的哪家模型？我们从 GPT-4 切到 Claude 之后延迟降了不少"

BAD reply examples (typical AI slop — avoid at all costs):
- "This is a fascinating perspective on AI development! I couldn't agree more with your point about..."
- "Great insight! As someone who works in this space, I find this incredibly relevant..."
- "Love this take. The intersection of AI and developer tooling is truly a game-changer."
- "非常认同！这个观点真的说到了AI开发者的心坎里，受益匪浅！"""


def _parse_llm_text_to_json(text: str) -> dict:
    text = _strip_markdown_fences(text)
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON in response: {text[:200]}")
    return json.loads(text[start:end])


def _call_llm_once(spec: dict, prompt: str) -> str:
    import urllib.request
    import urllib.error

    kind = (spec.get("kind") or _infer_llm_kind(spec.get("api_url", ""))).lower()
    max_tok = _effective_max_tokens_for_spec(spec, REPLY_MAX_TOKENS)
    payload = {
        "model": spec["model"],
        "max_tokens": max_tok,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}],
    }

    if kind == "anthropic":
        url = spec["api_url"].rstrip("/")
        if url.endswith("/v1"):
            url = url + "/messages"
        elif not url.endswith("/messages"):
            url = url + "/v1/messages"
    else:
        url = _openai_chat_completions_url(spec["api_url"])

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    if kind == "anthropic":
        # Anthropic API 使用 x-api-key header
        req.add_header("x-api-key", spec['api_key'])
        req.add_header("anthropic-version", "2023-06-01")
    else:
        # OpenAI 兼容 API 使用 Authorization Bearer
        req.add_header("Authorization", f"Bearer {spec['api_key']}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Server error '{e.code}' for url '{url}'"
        ) from e

    data = json.loads(raw)

    if kind == "anthropic":
        if data.get("type") != "message":
            err = data.get("error", {}).get("message") or json.dumps(data)[:300]
            raise RuntimeError(f"LLM 返回异常: {err}")
        parts = [item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"]
        text = "\n".join(parts).strip()
    else:
        err_obj = data.get("error")
        if err_obj:
            msg = err_obj.get("message") if isinstance(err_obj, dict) else str(err_obj)
            raise RuntimeError(f"LLM 返回异常: {msg or json.dumps(data)[:300]}")
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"LLM 返回无 choices: {json.dumps(data)[:300]}")
        msg = choices[0].get("message", {}) or {}
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
            text = "\n".join(parts).strip()
        else:
            text = str(content or "").strip()

    if not text:
        raise RuntimeError("LLM 返回为空")
    return text


def call_llm(prompt: str) -> tuple[dict, dict]:
    """返回 (回复 JSON, 实际调用元信息)。"""
    chain = _build_reply_llm_chain()
    if not chain:
        raise RuntimeError(
            "未配置可用 LLM：请设置 XPOST_LLM_API_KEY（及 URL/模型），或完整设置 XPOST_LLM_FALLBACK_API_URL、XPOST_LLM_FALLBACK_API_KEY、XPOST_LLM_FALLBACK_MODEL"
        )
    errors = []
    for spec in chain:
        try:
            text = _call_llm_once(spec, prompt)
            payload = _parse_llm_text_to_json(text)
            meta = {
                "llm_route": spec.get("label") or "primary",
                "llm_model": spec.get("model") or "",
                "llm_api_url": spec.get("api_url") or "",
            }
            return payload, meta
        except Exception as exc:
            label = spec.get("label") or "?"
            errors.append(f"{label}: {exc}")
    raise RuntimeError("所有 LLM 端点均失败: " + " | ".join(errors))


def _append_reply_runtime_log(meta: dict, ok: bool, error: str | None = None) -> None:
    """写入 xinfo/log/runtime/YYYY-MM-DD_reply-generate.jsonl，便于事后查看用了哪个模型。"""
    try:
        from datetime import datetime

        runtime_dir = _REPO_ROOT / "xinfo" / "log" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        path = runtime_dir / f"{today}_reply-generate.jsonl"
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "command": "reply-generate",
            "ok": ok,
            "llm_route": meta.get("llm_route"),
            "llm_model": meta.get("llm_model"),
            "llm_api_url": meta.get("llm_api_url"),
        }
        if error:
            entry["error"] = error[:500]
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # 日志失败不影响主流程
        pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: generate_replies.py <tweet_text> <handle>"}))
        sys.exit(1)

    tweet_text = sys.argv[1][:2000]
    handle = sys.argv[2]

    try:
        prompt = build_prompt(tweet_text, handle)
        result, meta = call_llm(prompt)
        # 保留 A/B/C 顶层字段，兼容现有调用方；追加模型元信息
        out = dict(result)
        out.update(meta)
        _append_reply_runtime_log(meta, ok=True)
        print(json.dumps(out, ensure_ascii=False))
    except Exception as e:
        _append_reply_runtime_log({}, ok=False, error=str(e))
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
