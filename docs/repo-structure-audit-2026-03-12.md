# gitxPost 仓库结构审计

日期：2026-03-12

## 结论

当前仓库已经具备开源可用的核心功能，但目录命名和职责边界还没有完全收干净。  
如果目标是“GitHub 开源 + 新用户一看就能上手”，现在最需要做的不是继续堆功能，而是把目录语义、示例文件、遗留命名和文档入口统一起来。

## 当前合理的部分

- `xpost.py`
  - 作为统一 CLI 入口是合理的
- `auto_publish_post.py` / `auto_publish_uc.py` / `grok_hot_posts.py`
  - 业务入口清晰，职责边界基本明确
- `browser_cdp_session.py`
  - 共享浏览器会话层独立出来是对的
- `CI/`
  - 测试用例和报告模板单独成目录是合理方向
- `docs/`
  - 适合放经验、设计、迁移记录
- `skills/`
  - 对开源用户来说是加分项，说明项目不仅能手工用，也能被 Agent 直接调用

## 当前不够理想的部分

### 1. `CreateMd/` 命名不够开源友好

问题：
- 语义偏“内部习惯”
- 新用户不容易第一眼理解它是“文章内容工作区”

建议：
- 后续可考虑重命名为 `content/`、`articles/` 或 `workspace/`

### 2. `pasreMarkDown/` 存在历史拼写问题

问题：
- 名字里有明显 typo
- 对开源项目不够专业

建议：
- 后续重命名为 `parse_markdown/`、`article_pipeline/` 或 `vendor/x_article_publisher/`
- 如果短期不改，README 里要明确说明这是历史保留目录

### 3. `config.py` 更像历史配置，不像当前主配置入口

问题：
- 配置内容偏旧
- 不像当前运行路径的唯一配置源

建议：
- 要么真正接入运行时
- 要么降级为“参考配置”
- 要么删除

### 4. `scripts/agent_example.py` 更像示例，不像核心脚本

建议：
- 后续可移动到 `examples/`

### 5. 历史测试文章与正式示例文章混在一起

问题：
- `CreateMd/testmd/` 与正式示例共存
- 开源用户不容易区分“推荐示例”和“历史测试残留”

建议：
- 保留 1 到 2 个正式示例
- 其余历史样本迁到 `examples/archive/` 或删除

## 推荐的下一步整理方向

### 最小整理版

- 保持现有代码结构不动
- 只修正 README、目录说明、历史目录注释
- 这是当前性价比最高的做法

### 中度整理版

- `CreateMd/` 改名
- `pasreMarkDown/` 改名
- `scripts/agent_example.py` 挪到 `examples/`
- `config.py` 清理

### 开源标准版

- 引入 `src/gitxpost/` 包结构
- CLI、浏览器会话、Article/Post/Grok 分模块
- 示例内容、文档、CI、skills 分区更彻底

## 当前建议

现在最适合的路线是“最小整理版”：

1. 先让 README 准确、完整、可上手
2. 明确哪些目录是历史保留
3. 把 CI、CHANGELOG、skills、工作流入口讲清楚
4. 后续再做目录重构

原因：
- 现在功能刚跑通，直接大改目录容易引入新问题
- 对开源第一阶段来说，文档清晰比目录完美更重要
