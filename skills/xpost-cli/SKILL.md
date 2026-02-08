---
name: xpost-cli
description: 使用本地 xpost CLI 处理 X Articles 的 Markdown 工作流。适用于中文请求如：生成文章骨架/模板、模板校验/预检、解析 Markdown 为 JSON、保存草稿或发布到 X Articles、xpost 命令、X 文章发布、Markdown 发布。
---
# xpost CLI Skill

## Scope
Use the local `xpost` CLI in this repo to:
- init: generate an article skeleton
- validate: enforce template constraints
- parse: produce structured JSON
- publish: save draft or publish
- doctor: check environment/deps

## Prerequisites
- Run inside the repo: `/Users/jackwl/Code/gitcode/gitxPost`
- venv is active and CLI installed: `pip install -e .`

## Commands

### Init
Create a skeleton article (optionally with topic/style):
```
xpost init CreateMd/your_article.md --topic "Your topic" --style zara
```

### Validate
Strictly validate against `CreateMd/template.md`:
```
xpost validate CreateMd/your_article.md
```

### Parse
Convert Markdown to structured JSON:
```
xpost parse CreateMd/your_article.md
```

### Publish
Default is draft; use `--publish` to publish:
```
xpost publish CreateMd/your_article.md
xpost publish CreateMd/your_article.md --publish
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
- If `publish` fails with module import errors, ensure you are in the repo and the venv is active
