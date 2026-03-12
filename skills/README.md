# Skills 说明

当前仓库里的 skills 分成两类：

## 1. 当前主入口 skills

这两份是当前仍在维护、推荐对外使用的 repo 级 skills：

- `skills/xpost-cli/SKILL.md`
  - 统一处理 Article / Post 的 CLI 工作流
- `skills/grok-hotposts-cli/SKILL.md`
  - 处理 Grok 热点搜索

## 2. 历史说明

历史上，Article 发布能力以独立 skill 形式存在。  
现在它已经不再是 repo 的主入口，而是被合并进 `xpost` CLI 的工作流里。

对应的脚本资产保留在：

- `article_tooling/scripts/`

历史背景说明统一收敛到：

- `docs/skill-topology-2026-03-12.md`

## 建议

- 新开发、新集成：优先使用 `skills/xpost-cli/` 和 `skills/grok-hotposts-cli/`
- 历史资料查阅：看 `docs/skill-topology-2026-03-12.md`
