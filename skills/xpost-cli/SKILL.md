---
name: xpost-cli
description: Use gitxPost's local xpost CLI to scaffold articles, generate real markdown from a skeleton, validate or parse markdown, save or publish X Articles, create X Posts, run X radar commands, initialize Post login sessions, and run doctor checks. Use when a user asks to run xpost commands, generate or publish an Article, publish a Post, run X radar, or troubleshoot the local gitxPost CLI.
---
# xpost CLI

## Use this skill when

- The user wants to run `xpost` commands
- The task involves `Article` draft or publish
- The task involves generating a full article from a markdown skeleton
- The task involves `Post` draft, image post, or `post-login`
- The task involves X radar scan, analysis, or account management
- The user wants to check whether the local gitxPost environment is healthy

## Preferred command pattern

Run from the repo root and prefer the explicit Python entrypoint:

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python xpost.py ...
```

Use `xpost` directly only if the editable CLI is already confirmed to work.

## Core workflows

### Environment check

```bash
python xpost.py doctor
```

If dependencies are missing, run:

```bash
./scripts/install_cli.sh
```

### Markdown workflow

```bash
python xpost.py init content/drafts/your_article.md --topic "Your topic" --style zara
python xpost.py generate content/drafts/your_article.md
python xpost.py validate content/drafts/your_article.md
python xpost.py parse content/drafts/your_article.md
```

If the repo is configured with `~/.openclaw/scripts/tokenmax.sh`, `generate` can call the local LLM API without extra flags.

### Article

Draft:

```bash
python xpost.py publish content/drafts/your_article.md --no-wait
```

Publish:

```bash
python xpost.py publish content/drafts/your_article.md --publish --no-wait
```

### Post

Text:

```bash
python xpost.py post "Hello world" --publish
```

Image post:

```bash
python xpost.py post "Image post" --images /absolute/path/to/image.png --publish
```

Login initialization:

```bash
python xpost.py post-login
```

### X Radar

Scan:

```bash
python xpost.py radar-scan
```

Analyze:

```bash
python xpost.py radar-analyze --days 7
```

Manage accounts:

```bash
python xpost.py radar-accounts list
python xpost.py radar-accounts add NewAccount "reason"
```

## Guardrails

- Confirm with the user before any real external publish action
- Use absolute image paths for `--images`
- Prefer `content/drafts/` for working files and `content/examples/` only for smoke or reference
- If the user is still writing or choosing a style, use `skills/content-workflow/` first, then come back here for publish
