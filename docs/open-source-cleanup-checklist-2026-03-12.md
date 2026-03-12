# 开源整理清单

日期：2026-03-12

## 立即做

- 继续以 `README.md` 作为唯一主入口
- 继续维护 `CHANGELOG.md`
- 继续维护 `CI/` 作为统一验收入口
- 继续以 `content/` 承载模板、Prompt、示例、草稿工作区
- 继续以 `article_tooling/` 承载 Article 解析与剪贴板脚本
- 继续保持 repo 顶层只保留两份活跃 skills

## 后续做

- 优化 `content/examples/` 中示例文件命名
- 优化 `article_tooling/scripts/` 的说明与示例
- 增加更多开源友好的 examples 和 quickstart 示例
- 如果未来功能继续扩大，再考虑 `src/gitxpost/` 包结构

## 不建议动

- 不建议现在继续大规模重构自动化主流程
- 不建议把 Article / Post / Grok 再统一抽象一层
- 不建议为了“更优雅”立即删除所有历史资料

## 原因

当前最应该保护的是：

- 已经跑通的 Article
- 已经跑通的 Post
- 已经跑通的 Grok

在这个基础上，当前更合理的节奏是：

1. 先把结构、文档、skills、CI 收干净
2. 再逐步优化命名和示例
3. 最后才考虑更大规模的架构重组
