---
name: content-workflow
description: Guide gitxPost's Markdown article workflow: choose a writing style, scaffold drafts, optionally run the Antigravity image workflow, validate and parse markdown, and prepare the result for X Article publish. Use when users ask to write an X article, choose zara or tech or fun prompt styles, add article images, or prepare markdown for publication.
---
# Content Workflow

## Use this skill when

- The user is still writing or planning an article
- The user asks which prompt style to use
- The user wants to scaffold a markdown article before publishing
- The user wants to prepare article images with the Antigravity workflow

## Style selection

- `zara`: product insight, experience sharing, tool recommendation
- `tech`: engineering walkthrough, architecture, implementation details
- `fun`: light, conversational, meme-friendly or science-pop tone

## Preferred workflow

### 1. Create a draft

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python xpost.py init content/drafts/your_article.md --topic "Your topic" --style tech
```

### 2. Write against the repo template

Use:

- `content/template.md`
- `content/prompt-guide.md`
- `content/prompts/`

### 3. Optional: auto-generate images with Antigravity

In Antigravity, run:

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

Use this only when the external Antigravity workflow is available.

### 4. Validate and parse before publish

```bash
python xpost.py validate content/drafts/your_article.md
python xpost.py parse content/drafts/your_article.md
```

### 5. Hand off for publish

When the markdown is ready, switch to `xpost-cli` for:

- `python xpost.py publish ...`

## Guardrails

- Use `content/drafts/` for in-progress writing
- Keep `content/examples/` as stable reference or smoke fixtures
- Do not jump straight to publish while the user is still choosing tone, structure, or images
