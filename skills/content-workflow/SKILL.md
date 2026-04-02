---
name: content-workflow
description: 引导 gitxPost 的 Markdown 文章工作流：选择写作风格、生成草稿骨架、用 xpost 生成真实文章、按需运行 Gemini Flash Image / Antigravity 配图流程、校验并解析 Markdown，并为 X Article 发布做准备。当用户提到写 X 文章、选择 zara 或 tech 或 fun 风格、添加文章配图、准备发布 Markdown 时使用。
---
# Content Workflow

## Use this skill when
- 帮我写文章、post、帖子
- 用户还在规划或撰写文章
- 用户在问该选哪种 prompt 风格
- 用户想在发布前先生成 Markdown 文章骨架
- 用户想把骨架稿补成真实成文
- 用户想给文章自动配图，或结合 Antigravity 处理文章配图

## Style selection

- `zara`：产品洞察、经验分享、工具推荐
- `tech`：工程拆解、架构分析、实现细节
- `fun`：轻松口语、梗感表达、偏科普语气

## Preferred workflow

### 1. Create a draft

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python xpost.py init content/drafts/your_article.md --topic "Your topic" --style tech
```

文章在 Web/API 流程里会统一落到 `xinfo/log/articles/<article_id>/`，其中 `article.json`、`article.md` 和 `images/` 各自独立。

### 2. Write against the repo template

- `content/template.md`
- `content/prompt-guide.md`
- `content/prompts/`

### 3. Generate the real article

推荐路径：

```bash
python xpost.py generate content/drafts/your_article.md
```

这个命令会读取 `xpost init` 写入文件顶部的风格 Prompt，并直接把可发布的 Markdown 文章回写到原文件。

人工兜底路径：

- 打开生成的 Markdown 草稿
- 复制顶部嵌入的 Prompt 区块到 Claude / OpenClaw / Codex
- 明确要求它只输出最终 Markdown，保留图片路径和文末结构

### 4. Optional: auto-generate images with Gemini Flash Image

如果当前仓库可直接运行本地配图命令，优先使用：

```bash
python xpost.py auto-img content/drafts/your_article.md --style zara
```

该命令会先用文本 LLM 规划配图 brief，再调用 Gemini Flash Image 生成真实图片并写回文章目录。
其中 `images/cover.png` 走横幅封面图模板，正文占位图则走 clean modern isometric / 示意图模板。

如果本地图像模型不可用、或需要更强的人工视觉控制时，再走 Antigravity 工作流。

在 Antigravity 中执行：

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

只有在外部 Antigravity 工作流可用时才走这一步。

### 5. Validate and parse before publish

```bash
python xpost.py validate content/drafts/your_article.md
python xpost.py parse content/drafts/your_article.md
```

### 6. Hand off for publish

当 Markdown 准备完成后，切换到 `xpost-cli` 做发布：

- `python xpost.py publish ...`

## Guardrails

- 写作中的内容优先放在 `content/drafts/`
- `content/examples/` 只保留稳定示例或 smoke 样本
- 当用户还在确定语气、结构或配图时，不要直接跳到发布步骤
