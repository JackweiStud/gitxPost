---
name: xpost-cli
description: 使用本地 xpost CLI 处理 gitxPost 的核心工作流。适用于中文请求如：生成文章骨架/模板、模板校验/预检、解析 Markdown 为 JSON、保存草稿或发布到 X Articles、发布 X Post、xpost 命令、Markdown 发布。
---
# xpost CLI Skill

## Scope
Use the local `xpost` CLI in this repo to:
- init: generate an article skeleton
- validate: enforce template constraints
- parse: produce structured JSON
- publish: save Article draft or publish
- post: save Post draft or publish
- post-login: initialize and persist Post login session
- doctor: check environment/deps

## Prerequisites
- Run inside the repo: `/Users/jackwl/Code/gitcode/gitxPost`
- .venv is active and CLI installed: `pip install -e .`

## Commands

### Init
Create a skeleton article (optionally with topic/style):
```
xpost init content/drafts/your_article.md --topic "Your topic" --style zara
```

### Validate
Strictly validate against `content/template.md`:
```
xpost validate content/drafts/your_article.md
```

### Parse
Convert Markdown to structured JSON:
```
xpost parse content/drafts/your_article.md
```

### Publish
Default is draft; use `--publish` to publish:
```
xpost publish content/drafts/your_article.md
xpost publish content/drafts/your_article.md --publish
```

### Post
Publish a short post or save a draft:
```
xpost post "Hello world" --publish
xpost post "Draft first" --no-wait
xpost post "Image post" --images /path/to/image.png --publish
```

### Post Login
Initialize the reusable Chrome login session for Post:
```
xpost post-login
```

### Doctor
Check environment and dependencies:
```
xpost doctor
```

## Output
All commands return JSON. For `publish`, the output includes:
- `missing_images`
- `missing_images_count`
- `timings` (parse_ms, publish_ms, total_ms)

## Usage Notes
- If dependencies are missing, run `./scripts/install_cli.sh`
- If `publish` fails with module import errors, ensure you are in the repo and `.venv` is active
