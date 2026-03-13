# Skill 拓扑说明

日期：2026-03-12

## 目标

说明这个仓库里多处 skill 资产之间的关系，避免后续维护时出现：

- 不知道哪个 skill 还在用
- 不知道哪些是 repo 主入口
- 不知道哪些只是历史遗留

## 当前结论

### 保留为主入口的 skills

- `skills/xpost-cli/SKILL.md`
  - 负责 Article / Post 的统一 CLI 能力
- `skills/x-radar-cli/SKILL.md`
  - 负责 X Radar 的 scan / analyze / daily / weekly / accounts
- `skills/grok-hotposts-cli/SKILL.md`
  - 负责 Grok 热点搜索
- `skills/content-workflow/SKILL.md`
  - 负责 Markdown 起稿、Prompt 选择、Antigravity 配图与发布前准备

### 已被合并的历史 skill

- `x-article-publisher`

它曾经是一个独立的 skill / plugin 形态。  
现在它的职责已经被拆成两部分：

1. 面向用户与 Agent 的主入口：`xpost` CLI
2. 面向内部复用的脚本资产：`article_tooling/scripts/`

因此它不再需要继续作为 repo 级活跃 skill 存在。

## 当前目录关系

```text
skills/
├── xpost-cli/
├── x-radar-cli/
├── grok-hotposts-cli/
├── content-workflow/
└── README.md

article_tooling/
└── scripts/
```

## 为什么这样拆

### `xpost-cli`

保留原因：

- 它是当前统一入口
- 覆盖 Article / Post / doctor / init / parse / validate / generate
- 对 repo 用户最直接

### `x-radar-cli`

保留原因：

- Radar 的用户意图与“发内容”明显不同
- 包含 scan / analyze / daily / weekly / accounts，一套职责自洽
- 更适合 OpenClaw / Codex agent 做情报任务时稳定触发

### `grok-hotposts-cli`

保留原因：

- 与 `xpost` CLI 不同，它是独立脚本入口
- 主题明确，边界清晰

### `content-workflow`

保留原因：

- 把“写内容”和“发内容”拆开，降低 skill 触发歧义
- 能把 Prompt、模板、Antigravity workflow 收在一个入口里
- 更适合 Codex agent 在内容准备阶段使用

### `x-article-publisher`

不再保留为主入口的原因：

- 功能已经被 `xpost publish` 吸收
- 若继续并列维护，会造成双入口和文档重复
- 其真正有价值的部分是脚本资产，而不是继续作为 repo 顶层 skill

## 后续建议

### 立即执行

- repo 顶层维护 `xpost-cli`、`x-radar-cli`、`grok-hotposts-cli`、`content-workflow`
- 历史 skill 说明只保留在文档

### 后续可选

- 历史说明只保留在当前文档，不再单独维护旧 skill / plugin 文件
- 如果未来 Radar 与 Grok 的职责进一步重叠，再决定是否继续收口 skill 数量
