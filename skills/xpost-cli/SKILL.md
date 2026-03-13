---
name: xpost-cli
description: 使用 gitxPost 本地 xpost CLI 处理文章骨架生成、文章成文、Markdown 校验与解析、X Articles 草稿或发布、X Post 发布、Post 登录初始化以及 doctor 环境检查。当用户提到运行 xpost 命令、生成或发布文章、发布 Post、初始化 Post 登录态、排查 gitxPost CLI 问题时使用。
---
# xpost CLI

## Use this skill when

- 用户想运行 `xpost` 命令
- 任务涉及 `Article` 草稿或发布
- 任务涉及把 Markdown 骨架生成成完整文章
- 任务涉及 `Post` 草稿、图文 Post 或 `post-login`
- 用户想检查本地 gitxPost 环境是否正常

## Preferred command pattern

在仓库根目录执行，优先使用显式 Python 入口：

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python xpost.py ...
```

只有在已经确认 editable CLI 可用时，才直接使用 `xpost`。

## Core workflows

### Environment check

```bash
python xpost.py doctor
```

如果依赖缺失，执行：

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

`generate` 会从项目 `.env` 或当前 shell 环境变量读取 LLM 配置。

### Article

草稿：

```bash
python xpost.py publish content/drafts/your_article.md --no-wait
```

发布：

```bash
python xpost.py publish content/drafts/your_article.md --publish --no-wait
```

### Post

纯文本：

```bash
python xpost.py post "Hello world" --publish
```

图文 Post：

```bash
python xpost.py post "Image post" --images /absolute/path/to/image.png --publish
```

登录初始化：

```bash
python xpost.py post-login
```

## Guardrails

- 任何真实外发动作前，都先和用户确认
- `--images` 使用绝对路径
- 工作文件优先放在 `content/drafts/`，`content/examples/` 只作为 smoke 或参考
- 如果用户还在写作、定风格、定结构，先用 `skills/content-workflow/`，准备好后再回到这里发布
- 如果用户要做 X Radar 的扫描、分析、日报、周报或账号管理，改用 `skills/x-radar-cli/`
