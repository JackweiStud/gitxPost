---
name: grok-hotposts-cli
description: Use gitxPost's local Grok collector to search X hot posts and return structured JSON. Use when the user asks for X or Twitter hot posts, recent trends, topic research, Grok-based search, or OpenClaw and GitHub topic summaries.
---
# Grok Hot Posts CLI

## Use this skill when

- The user wants X or Twitter hot posts
- The user wants recent topic research from Grok
- The task is to collect structured JSON for a topic such as AI, OpenClaw, GitHub, or market chatter

## Preferred command pattern

Run from the repo root and prefer JSON stdout:

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python grok_hot_posts.py --json-only --topics "OpenClaw skills GitHub" --hours 168 --count 5
```

## Working rules

- Prefer `--json-only` unless the user explicitly wants files saved to `hot_posts_output/`
- Treat this as a long-running command; do not abort early just because stdout is empty
- Progress is emitted during execution; wait for the final JSON before summarizing results
- After the command completes, present the actual posts to the user instead of only mentioning an output file

## Output expectations

Return or summarize:

- `time`
- `author`
- `summary`
- `views`
- `likes`
- `reposts`
- `url`

## Guardrails

- This workflow depends on a logged-in X session and Grok access
- Results depend on external X and Grok availability, so occasional retries may be needed
- If the user wants markdown drafting or X publishing, use `xpost-cli` or `content-workflow` instead
