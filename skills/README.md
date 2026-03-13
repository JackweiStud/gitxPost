# Skills 说明

当前仓库里的 skills 现在按 Codex / OpenClaw 更容易理解的职责拆成四类：

## 1. 当前主入口 skills

这四份是当前仍在维护、推荐给 Codex agent 使用的 repo 级 skills：

- `skills/xpost-cli/SKILL.md`
  - 统一处理 Article / Post 的 CLI 执行与发布
- `skills/x-radar-cli/SKILL.md`
  - 统一处理 X Radar 的扫描、分析、日报、周报与账号管理
- `skills/grok-hotposts-cli/SKILL.md`
  - 处理 Grok 热点搜索与 JSON 输出
- `skills/content-workflow/SKILL.md`
  - 处理 Markdown 起稿、Prompt 选择、Antigravity 配图与发布前准备

每个活跃 skill 现在都带有：

- `SKILL.md`
- `agents/openai.yaml`

这样更适合后续给 Codex agent 直接接入和展示。

## 2. 历史说明

历史上，Article 发布能力以独立 skill 形式存在。  
现在它已经不再是 repo 的主入口，而是被合并进 `xpost` CLI 的工作流里。

对应的脚本资产保留在：

- `article_tooling/scripts/`

历史背景说明统一收敛到：

- `docs/skill-topology-2026-03-12.md`

## 建议

- 新开发、新集成：优先使用这四份 skills
- 写内容时先用 `content-workflow`
- 真正执行发布时再切到 `xpost-cli`
- 做 X 情报扫描与周报生产时使用 `x-radar-cli`
- 做热点搜索时使用 `grok-hotposts-cli`
- 历史资料查阅：看 `docs/skill-topology-2026-03-12.md`
