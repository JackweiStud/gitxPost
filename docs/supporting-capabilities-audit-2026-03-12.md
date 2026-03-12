# 支撑能力审计

日期：2026-03-12

## 审计范围

- Markdown 创作与模板
- 多风格 Prompt
- Antigravity 自动配图工作流
- `xpost` CLI
- skills 集成

## 结论

这 5 部分整体可用，而且经过第二轮整理后，对外的一致性已经比之前明显更好。

当前排序后的判断如下：

## P0：`xpost` CLI

### 状态

- 可作为统一入口继续保留
- `init / validate / parse / publish / post / post-login / doctor` 结构完整

### 本轮改进

- 运行路径切到 `content/` 与 `article_tooling/`
- `doctor` 已和当前真实依赖对齐
- `init` 已可自动补示例图片

### 结论

- 当前是正确的主入口
- 不建议再保留第二套 repo 级 Article 发布入口

## P1：Markdown 创作与模板

### 状态

- `content/template.md` 仍然有效
- `content/prompt-guide.md` 可作为写作入口
- `content/examples/` 的示例结构已经比旧版清楚

### 结论

- 当前能力正确
- 后续只需要继续优化示例文件命名，不需要重做机制

## P1：多风格 Prompt

### 状态

- `content/prompts/prompt_zara.md`
- `content/prompts/prompt_tech.md`
- `content/prompts/prompt_fun.md`

三份 Prompt 仍然有效，且与当前模板规范兼容。

### 结论

- 能继续保留
- 建议后续补一个更面向开源用户的选型指南

## P2：Antigravity 自动配图工作流

### 状态

- `.agent/workflows/auto-imgByMdCn.md` 仍然存在
- 工作流说明本身没有问题

### 边界

- 它依赖 Antigravity 运行环境
- 不属于本仓库可独立全自动验收的能力

### 结论

- 可以保留
- 但必须一直明确它是“集成能力”，不是“仓库内裸脚本能力”

## P1：skills 集成

### 状态

- `skills/xpost-cli/` 与 `skills/grok-hotposts-cli/` 现在是 repo 主入口
- 历史 `x-article-publisher` 已下沉为 `article_tooling/legacy_*`

### 结论

- 这种拆分是正确的
- 现在的 skill 关系比之前清楚很多

## 最终判断

这几块能力目前不存在“主流程错误”的问题。  
当前更大的价值，不在继续重写功能，而在继续保证：

- 文档和代码路径一致
- repo 级 skills 入口单一
- 历史资产不再和当前入口混在一起
