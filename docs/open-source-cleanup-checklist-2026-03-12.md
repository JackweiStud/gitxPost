# 开源整理清单

日期：2026-03-12

## 立即做

- 保持 `README.md` 为唯一主入口，持续对齐真实功能和当前技术路线
- 维护 `CHANGELOG.md`，确保每次提交前更新
- 继续维护 `CI/` 目录，作为统一验收入口
- 保持 `requirements.txt`、`pyproject.toml`、`doctor` 与真实依赖一致
- 保持 `skills/` 文档和真实 CLI 用法一致
- 明确 `chrome_data_mirror/` 和 `patchright_post_data/` 只作为本地运行态，不提交 Git

## 后续做

- 将 `CreateMd/` 重命名为更直观的目录，例如 `content/` 或 `articles/`
- 将 `pasreMarkDown/` 重命名为无 typo 的目录
- 将 `CreateMd/testmd/` 的历史样例迁移到 `examples/archive/`
- 将 `scripts/agent_example.py` 移动到更合适的示例目录
- 收敛 `config.py` 的定位：真正接入或删除
- 给 Prompt 能力补一份独立说明文档
- 给 Antigravity 配图工作流补一份“依赖边界与接入方式”文档
- 逐步把仓库整理成更标准的模块化结构

## 不建议动

- 现在不要直接大规模重构核心自动化代码目录
- 现在不要为了“更优雅”就立即把 Article、Post、Grok 再统一抽象一层
- 现在不要在功能刚稳定后立即改掉所有历史目录名

## 原因

当前仓库最宝贵的是：

- Article 已重新打通
- Post 纯文本和图文已跑通
- Grok JSON 输出已可用

在这个时间点，最应该保护的是稳定性和交付信心。  
因此当前更合适的策略是：

1. 先把文档、依赖、安装、验收入口收干净
2. 再做目录和模块化的中度整理
3. 最后才是更大规模的开源结构重构
