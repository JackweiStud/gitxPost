---
name: grok-hotposts-cli
description: 使用 gitxPost 本地 Grok 采集器搜索 X 热门帖子并返回结构化 JSON。当用户提到 X 或 Twitter 热帖、近期趋势、主题调研、基于 Grok 的搜索、OpenClaw 或 GitHub 话题摘要时使用。
---
# Grok Hot Posts CLI

## Use this skill when
- X、推特的XX热点、新闻
- 用户想查看 X 或 Twitter 热帖
- 用户想做基于 Grok 的近期主题调研
- 任务需要围绕 AI、OpenClaw、GitHub 或市场话题采集结构化 JSON

## Preferred command pattern

在仓库根目录执行，优先输出 JSON 到 stdout：

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python grok_hot_posts.py --json-only --topics "OpenClaw skills GitHub" --hours 168 --count 5
```

## Working rules

- 除非用户明确要求落文件到 `hot_posts_output/`，否则优先使用 `--json-only`
- 这是长耗时命令，不要因为一开始 stdout 没内容就提前中断
- 执行过程中会持续输出进度，先等待最终 JSON，再总结结果
- 命令结束后，优先把真实帖子内容总结给用户，而不是只说生成了某个文件

## Output expectations

返回或总结时，优先包含：

- `time`
- `author`
- `summary`
- `views`
- `likes`
- `reposts`
- `url`

## Guardrails

- 这条链路依赖已登录的 X 会话和可用的 Grok
- 结果受外部 X 与 Grok 可用性影响，偶发重试是正常情况
- 如果用户要写 Markdown、生成文章或发布到 X，改用 `xpost-cli` 或 `content-workflow`
