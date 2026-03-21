#!/usr/bin/env python3
"""
读取推文内容，调用 gitxPost .env 里的 LLM，生成 3 条回复备选。
用法: python generate_replies.py "<tweet_text>" "<handle>"

输出 JSON: {"A": "...", "B": "...", "C": "..."}
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path("/Users/jackwl/Code/gitcode/gitxPost/.env")
load_dotenv(ENV_PATH)

API_KEY = os.getenv("XPOST_LLM_API_KEY", "")
API_URL = os.getenv("XPOST_LLM_API_URL", "")
MODEL = os.getenv("XPOST_LLM_MODEL", "claude-opus-4-6")

if not API_KEY:
    print(json.dumps({"error": "XPOST_LLM_API_KEY not set in .env"}))
    sys.exit(1)


def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r"^```[\w]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def _is_anthropic_api(url: str) -> bool:
    return "anthropic" in url.lower() or "claude" in url.lower()


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


def call_llm(prompt: str) -> dict:
    import httpx

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    if _is_anthropic_api(API_URL):
        headers["Anthropic-Version"] = "2023-06-01"
        payload = {
            "model": MODEL,
            "max_tokens": 1024,
            "temperature": 0.7,
            "messages": [{"role": "user", "content": prompt}],
        }
    else:
        payload = {
            "model": MODEL,
            "max_tokens": 1024,
            "temperature": 0.7,
            "messages": [{"role": "user", "content": prompt}],
        }

    with httpx.Client(timeout=120) as client:
        resp = client.post(API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if _is_anthropic_api(API_URL):
        if data.get("type") != "message":
            err = data.get("error", {}).get("message") or json.dumps(data)[:300]
            raise RuntimeError(f"LLM 返回异常: {err}")
        parts = [item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"]
        text = "\n".join(parts).strip()
    else:
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"LLM 返回无 choices: {json.dumps(data)[:300]}")
        text = choices[0].get("message", {}).get("content", "").strip()

    if not text:
        raise RuntimeError("LLM 返回为空")

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


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: generate_replies.py <tweet_text> <handle>"}))
        sys.exit(1)

    tweet_text = sys.argv[1][:2000]
    handle = sys.argv[2]

    try:
        prompt = build_prompt(tweet_text, handle)
        result = call_llm(prompt)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
