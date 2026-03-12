# 支撑能力审计

日期：2026-03-12

## 审计范围

- Markdown 创作与模板
- 多风格 Prompt
- Antigravity 自动配图工作流
- `xpost` CLI
- skills 集成

## 结论

这 5 部分整体是可用的，但它们的问题主要集中在“配套层不一致”，不是主流程不可用。

按优先级排序后，当前最值得关注的是：

1. `xpost doctor`、`requirements.txt`、`pyproject.toml` 的口径要和当前真实运行架构一致
2. `scripts/install_cli.sh`、skills 文档里的环境路径要统一到 `.venv`
3. 主文档与 skill 文档要明确项目已经不仅仅是 X Article 工具
4. Antigravity workflow 当前可作为工作流说明存在，但不属于仓库内可独立自测的能力

## P0：`xpost` CLI 配套口径

### 现状

- `xpost init`、`validate`、`parse` 可直接运行
- `xpost publish`、`post`、`doctor` 都是当前核心入口
- 主 CLI 本身可用

### 已验证

- `python xpost.py init /tmp/gitxpost_readme_audit.md --topic 'README audit topic' --style tech --force`
- `python xpost.py validate CreateMd/articleNew.md`
- `python xpost.py parse CreateMd/articleNew.md`
- `python xpost.py --help`
- `python xpost.py publish --help`
- `python xpost.py post --help`

### 问题

- `doctor` 仍按旧依赖模型检查 `undetected_chromedriver`、`selenium`、`markdown`、`bs4`、`html2text`
- `pyproject.toml` 和 `requirements.txt` 仍保留旧依赖

### 处理结论

- 这类问题会直接损害开源体验
- 需要优先和当前 Patchright + 本地 Chrome 架构对齐

## P1：Markdown 创作与模板

### 现状

- `CreateMd/template.md` 仍然能作为最低格式规范使用
- `xpost init` 生成的骨架也符合当前 Article 发布链路需要

### 问题

- `CreateMd/` 命名偏内部习惯
- 示例文章与历史测试样例仍有混放

### 处理建议

- 当前不急着重构
- 先在 README 里解释清楚，再在后续开源整理时处理

## P1：多风格 Prompt

### 现状

- `prompt_zara.md`
- `prompt_tech.md`
- `prompt_fun.md`

三份 Prompt 都存在，内容结构完整，且与当前 Markdown 模板兼容。

### 问题

- Prompt 文档和 `xpost init` 的关系目前主要靠 README 说明
- 还没有“哪种主题适合哪种风格”的更细操作指南

### 处理建议

- 当前保持不动
- 后续可补一个 `docs/writing-styles.md`

## P2：Antigravity 自动配图工作流

### 现状

- `.agent/workflows/auto-imgByMdCn.md` 存在
- 工作流说明完整，适合作为 Agent 工作流定义

### 问题

- 它依赖 Antigravity 运行环境，不是这个仓库单独可执行的脚本
- 也就是说，它是“集成能力说明”，不是“本仓库内可完全自测能力”

### 处理建议

- README 里明确写清依赖边界
- 不要把它描述成仓库自带的一键本地脚本能力

## P1：skills 集成

### 现状

- `skills/xpost-cli/SKILL.md`
- `skills/grok-hotposts-cli/SKILL.md`

两份 skill 都是有效资产，能帮助 Agent 直接用这个仓库。

### 问题

- 文案里有旧的 `venv` 路径
- `grok-hotposts-cli` 之前还沿用了旧的“文件输出优先”描述，不完全贴合现在 `--json-only` 的主路径
- `xpost-cli` 的能力描述偏旧，没覆盖 `post`

### 处理建议

- 保持 skill 目录结构不动
- 文案要及时和真实 CLI 对齐

## 总结

这部分能力不是“坏了”，而是“需要收口”。

最重要的判断：

- 主功能已经能跑
- 配套文档、依赖定义、安装脚本、skill 说明还需要持续对齐
- 这些内容非常影响 GitHub 开源体验，优先级高于进一步堆新功能
