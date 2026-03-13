---
name: x-radar-cli
description: 使用 gitxPost 本地 xpost CLI 处理 X 雷达扫描、分析、日报生成、周报生成和监控账号管理。当用户提到扫描 X 信息源、分析雷达结果、生成雷达日报或周报、管理监控账号时使用。
---
# X Radar CLI

## Use this skill when

- 用户想运行 X 雷达相关命令
- 任务涉及雷达扫描或分析
- 任务涉及生成X雷达日报
- 任务涉及生成X雷达周报
- 任务涉及管理（增删改查）监控中的 X 账号

## Preferred command pattern

在仓库根目录执行，优先使用显式 Python 入口：

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python xpost.py ...
```

只有在已经确认 editable CLI 可用时，才直接使用 `xpost`。

## Core workflows

### Scan

```bash
python xpost.py radar-scan
```

### Analyze

```bash
python xpost.py radar-analyze --days 7
```

### Daily report

```bash
python xpost.py radar-daily
```

默认输出：

- `xinfo/log/day/YYYY-MM-DD.md`
- `xinfo/log/actions.json`

### Weekly report

```bash
python xpost.py radar-weekly
```

默认输出：

- `xinfo/log/week/YYYY-MM-DD.md`
- `xinfo/log/actions.json`

### Manage accounts

```bash
python xpost.py radar-accounts list
python xpost.py radar-accounts add NewAccount "reason"
python xpost.py radar-accounts remove NewAccount
python xpost.py radar-accounts restore NewAccount
```

## Guardrails

- 优先读取生成后的文件，不要只依赖 stdout
- 日报 cron 推荐顺序：`radar-scan` -> `radar-analyze --days 7` -> `radar-daily`
- 周报 cron 推荐顺序：`radar-analyze --days 7` -> `radar-weekly`
- `radar-daily` 和 `radar-weekly` 会从项目 `.env` 或当前 shell 环境变量读取 LLM 配置
- Telegram 或其他分发动作建议放在 skill 之外处理
