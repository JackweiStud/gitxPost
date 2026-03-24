# gitxPost 迁移 Change Log

## 维护规则

- 每次准备执行 `git commit` 之前，必须先更新本文件。
- 变更记录至少要包含：
  - 本次改动影响的模块
  - 关键代码调整
  - 实际验证结果
  - 仍未解决的边界或风险
- 如果改动影响验收方式或测试结论，需要同步更新 `CI/` 目录下的文档。

日期：2026-03-24

## 本次补充：日报推文 URL 去重（源头 + 解析双重保障）

范围：
- `xpost.py` — 日报生成 prompt
- `web/api/server.py` — 日报解析

### 1. 源头 prompt 约束（xpost.py）

变更：
- 在 `_build_radar_daily_prompt` 的第 8 条规则中追加：**同一 URL 只能在最相关的一个分类中出现一次，禁止跨分类重复引用同一推文**
- AI 在生成日报时会遵循此约束，从源头减少重复

### 2. 解析层兜底（server.py）

变更：
- `_parse_daily_report` 在解析 `•` 开头的推文行时，新增 `seen_urls` 集合用于跟踪已处理的 URL
- 即使 AI 输出仍有重复，解析层会过滤，只保留第一次出现的版本

效果：
- 双重保障，确保用户在"推文精选"卡片区不会看到重复内容

---

## 本次补充：P2.2 推文卡片唯一 ID + P2.6 深色模式切换

范围：
- `web/ui/src/stores/app.js`
- `web/ui/src/App.vue`
- `web/ui/src/style.css`
- `web/ui/src/views/RadarDaily.vue`

### 1. P2.2 修复：推文卡片选中改为索引

变更：
- `RadarDaily.vue` 中 `toggleTweet` 现在接收卡片索引（`idx`）而非 `tweet.url`
- `selectedTweets` 数组存储的是选中卡片的索引列表
- `sendSelectedToReply` 根据索引从 `reportData.tweets` 中获取实际 URL

效果：
- 即使多张卡片引用相同 URL，点击一张只选中该张，不会联动选中同 URL 的其他卡片

### 2. P2.6 实现：深色模式切换

变更：
- `app.js` store 新增 `darkMode` 响应式状态、`toggleDarkMode` 方法
- 初始化时从 `localStorage` 读取或跟随系统偏好，并通过 `watch` 自动应用
- `style.css` 新增 `:root.dark` 变量覆盖（深色背景、浅色文字、调整阴影与高亮色）
- `App.vue` 侧边栏底部新增主题切换按钮（太阳/月亮图标），折叠时仅显示图标

效果：
- 用户可点击按钮在亮色/深色间切换，设置持久化到 `localStorage`

---

## 本次补充：Web UI 亮色主题、日报排版、流水线可中止

范围：
- `web/ui`（`style.css`、`App.vue`、`Dashboard.vue`、`RadarDaily.vue`、`api/xpost.js`、`index.html`）
- `web/api/server.py`

### 1. 一键日报可停止 / 减少重复并行

变更：
- 后端为 `_run_xpost` 增加全局互斥锁，同一时间仅允许一个 xpost 子进程，避免多标签重复点「一键」时抢同一浏览器实例。
- 跟踪当前子进程，新增 `POST /api/radar/cancel`，对活动进程 `kill` 以中断扫描/分析/日报/回帖等经 `_run_xpost` 启动的任务。
- 概览页流水线支持 `AbortController` 中止当前 HTTP 请求，并展示「停止」按钮与耗时说明；停止过程中展示「正在停止」状态。

效果：
- 用户可在长时间任务中途主动终止，避免只能干等或重复启动。

边界：
- 所有走 `_run_xpost` 的接口会串行排队；独立子进程（如 `reply/generate` 脚本）不受 `cancel` 影响。

### 2. 界面主题：明亮、偏产品感（参考 Google Stitch / M3）

变更：
- 全局 token 改为浅底、白卡片、圆角胶囊按钮与柔和阴影；主色采用近 Google Blue；侧栏 Logo 使用渐变块；主内容区轻量径向渐变衬底。
- Toast 改为浅色成功/错误底，避免「昏暗 AI 控制台」观感。

### 3. 「完整日报」Markdown 可读性

变更：
- `marked` 启用 `gfm` + `breaks`；全局 `.markdown-body` 限制行长（约 `42rem`）、优化列表/引用/链接样式；日报卡片内增加 `.report-prose` 容器。
- 修复日报页加载动画：补充 `@keyframes spin`。

### 4. 验证

已验证：
- `./.venv/bin/python -m py_compile web/api/server.py`

未验证（需本地起服务人工点选）：
- 浏览器内停止流水线与 cancel 联调全流程

---

日期：2026-03-13

## 本次补充：补强 Radar 日报/周报落盘前的 Markdown 提纯

范围：
- `radar-daily` / `radar-weekly` 文件落盘稳定性

### 1. 写文件前再次提取真正的 Markdown 正文

涉及文件：
- `xpost.py`

变更：
- 新增 `_extract_markdown_from_text()`
- 在 `radar-daily` 和 `radar-weekly` 写文件前，对 `report_json["markdown"]` 再做一次提纯
- 如果内容本身仍然是 `{"markdown":"..."}` 这类外层 JSON 包裹文本，会先抽取出真正的正文，再写入日报/周报文件

效果：
- 避免上游返回半残 JSON 或多包一层 JSON 时，把整段结构化文本直接写进 `.md` 产物
- 一旦 LLM 请求成功，落盘结果更接近纯 Markdown 正文，而不是 JSON 壳

### 2. 本次验证

已验证：
- `./.venv/bin/python -m py_compile xpost.py`

当前边界：
- 这次修复只增强“成功响应后的落盘提纯”
- 若上游 LLM 仍处于 `service_busy` / cooldown，`radar-daily` 本身仍可能失败，需要等上游恢复后再看真实新产物

## 本次补充：修复 Radar 日报正文被 JSON 包裹写入的问题

范围：
- `radar-daily` / `radar-weekly` 正文提取修复

### 1. 修复畸形 JSON 响应被误当作 Markdown 正文的问题

涉及文件：
- `xpost.py`

变更：
- 调整 `_normalize_radar_report_payload()`
- 当 LLM 返回无法解析为合法 JSON 时，不再直接把整段原始文本当成 markdown
- 只有当原始文本本身看起来像日报 / 周报正文时，才作为 markdown 接受

效果：
- 避免将 `{"markdown": "...", "actions": [...]}` 这类原始 JSON 文本直接写入 `xinfo/log/day/YYYY-MM-DD.md`
- Radar 日报 / 周报输出更稳定，产物更符合“纯 Markdown 正文”预期

### 2. 实际处理结论

说明：
- 这次在真实执行 `xpost.py radar-daily` 时，没有稳定复现此前的 `tokenmax.vip` SSL 错误
- 但排查过程中确认了一处更隐蔽的问题：模型返回内容可用时，仍可能因解析边界导致日报文件被写成 JSON 包裹文本
- 本次修复针对的正是这类“命令看似成功，但产物格式不对”的问题

## 本次补充：修复 Radar 日报 / 周报 LLM 返回兜底并补运行日志

范围：
- `radar-daily` / `radar-weekly` 稳定性修复
- 雷达运行日志落盘
- README / xinfo README 补充说明

### 1. 修复 Radar 报告生成对 LLM 返回格式过于脆弱的问题

涉及文件：
- `xpost.py`

变更：
- `radar-daily` / `radar-weekly` 的报告生成改为三层兜底：
  - 正常 JSON 解析
  - 强约束 JSON 重试
  - 直接返回 Markdown 正文的最终兜底
- 增加“看起来像日报 / 周报正文”的判定，避免把普通 JSON 字符串误当成 Markdown
- 新增 `RadarReportGenerationError`，失败时保留尝试记录，便于排查

效果：
- 解决 `python xpost.py radar-daily` 偶发报错 `LLM 未返回 markdown` 的问题
- 模型即使没有完全按 JSON 契约返回，也更容易被成功接住

### 2. 新增 Radar 运行日志

涉及文件：
- `xpost.py`

变更：
- `radar-daily` 每次运行会写入 `xinfo/log/runtime/YYYY-MM-DD_radar-daily.jsonl`
- `radar-weekly` 每次运行会写入 `xinfo/log/runtime/YYYY-MM-DD_radar-weekly.jsonl`
- 日志内容包含：
  - 输入文件路径
  - 输出文件路径
  - 模型名
  - 尝试记录
  - 错误信息
  - 原始响应摘要

效果：
- 后续再出现 LLM 返回结构异常时，不需要靠现场复现
- 可以直接从 runtime log 判断是模型没回、回空、还是返回结构变形

### 3. 补充文档：`interests.json` 是筛选核心文件

涉及文件：
- `README.md`
- `xinfo/README.md`

变更：
- 明确写入：`xinfo/log/interests.json` 是雷达日报 / 周报筛选标准的核心文件
- 补充 runtime log 路径说明

效果：
- 新同事和自动化任务更容易理解为什么要先同步兴趣画像
- 后续排查 Radar 问题时知道优先看哪里

### 4. 实际验证

执行：
- `./.venv/bin/python -m py_compile xpost.py`
- `./.venv/bin/python xpost.py radar-daily`

结果：
- `radar-daily` 成功生成：
  - `xinfo/log/day/2026-03-13.md`
- 并成功记录运行日志：
  - `xinfo/log/runtime/2026-03-13_radar-daily.jsonl`

## 本次补充：移除 tokenmax.sh 回退，统一改为 `.env`

范围：
- `xpost` LLM 配置来源收口
- README / 使用指南 / skill 文档同步

### 1. 移除 `~/.openclaw/scripts/tokenmax.sh` 代码依赖

涉及文件：
- `xpost.py`

变更：
- 删除 `TOKENMAX_SCRIPT` 常量
- 删除 `_read_tokenmax_config()`
- `generate`、`radar-daily`、`radar-weekly` 不再从 `tokenmax.sh` 读取 API Key / URL / model
- 统一只从项目根目录 `.env` 或当前 shell 环境变量读取：
  - `XPOST_LLM_API_KEY`
  - `XPOST_LLM_API_URL`
  - `XPOST_LLM_MODEL`
  - `XPOST_RADAR_LLM_MODEL`

效果：
- 项目配置入口更单一
- 同事不再依赖本机 OpenClaw 私有脚本
- 开源与交接时更容易解释

### 2. 补充 `.env` 配置示例与文档

涉及文件：
- `.env.example`
- `.gitignore`
- `README.md`
- `docs/usage-and-ignore-guide-2026-03-12.md`
- `skills/xpost-cli/SKILL.md`

变更：
- 新增 `.env.example`
- `.gitignore` 忽略 `.env`
- README 和使用指南改为明确推荐 `.env`
- skill 文档去掉 `tokenmax.sh` 回退说明

效果：
- 新同事按 `.env.example` 就能配置本地 LLM
- 项目文档与当前代码行为一致

### 3. 拆分 Radar 专用 skill

涉及文件：
- `skills/xpost-cli/SKILL.md`
- `skills/xpost-cli/agents/openai.yaml`
- `skills/x-radar-cli/SKILL.md`
- `skills/x-radar-cli/agents/openai.yaml`
- `skills/README.md`
- `README.md`
- `docs/skill-topology-2026-03-12.md`
- `docs/supporting-capabilities-audit-2026-03-12.md`

变更：
- 将 Radar 相关触发从 `xpost-cli` 中拆出
- 新增 `x-radar-cli`，专门负责 scan / analyze / daily / weekly / accounts
- `xpost-cli` 收窄为 Article / Post / doctor / generate / validate / publish

效果：
- OpenClaw / Codex agent 更容易按用户意图命中正确 skill
- 减少“发内容”和“做情报”两类任务的触发歧义

## 本次补充：Radar 日报/周报第一版开发

范围：
- Radar 日报/周报设计文档补充
- `xpost` Radar 日报与周报 CLI
- README / xinfo / CI / skills 文档同步

### 1. Radar 日报/周报命令落地

涉及文件：
- `xpost.py`

变更：
- 新增 `xpost radar-daily`
- 新增 `xpost radar-weekly`
- 两条命令默认复用 TokenMax API Key / URL，并默认使用 `claude-opus-4-6`
- `radar-daily` 基于 `RESULT.json + interests.json` 生成 `xinfo/log/day/YYYY-MM-DD.md`
- `radar-weekly` 基于 `*_analysis.json + actions.json` 生成 `xinfo/log/week/YYYY-MM-DD.md`
- 两条命令都会将新增行动追加到 `xinfo/log/actions.json`
- 为 LLM 调用补充 JSON 容错、一次重试，以及 `curl --http1.1` 与轻量网络重试

效果：
- Radar 不再只有“扫”和“分析”，开始具备正式的日报/周报生产层
- 后续 OpenClaw cron 可以直接消费落地 Markdown，而不是依赖命令 stdout

### 2. Radar 设计文档补充

涉及文件：
- `docs/radar-daily-migration-design-2026-03-13.md`

变更：
- 补充“推荐 cron 执行顺序”
- 明确 `*_analysis.json` 的生产者是 `radar-analyze`
- 明确周报正文归档推荐为 `xinfo/log/week/YYYY-MM-DD.md`
- 明确日报与周报默认使用 TokenMax Opus

效果：
- 后续日报/周报调度顺序、文件语义和模型口径统一

### 3. README / xinfo / CI / skill 文档同步

涉及文件：
- `README.md`
- `xinfo/README.md`
- `CI/test-cases.md`
- `CI/report-template.md`
- `skills/xpost-cli/SKILL.md`

变更：
- README 与 `xinfo/README.md` 增加 `radar-daily` / `radar-weekly` 用法与结果文件说明
- CI 新增 `TC-10 Radar 日报生成` 与 `TC-11 Radar 周报生成`
- `xpost-cli` skill 增加 Radar 日报/周报说明

效果：
- 日报/周报能力的使用方式、验收方式和 Agent 入口保持一致

### 本次验证

已验证：
- `python -m py_compile xpost.py`
- `python xpost.py radar-daily --help`
- `python xpost.py radar-weekly --help`
- `python xpost.py radar-daily --output /tmp/gitxpost-radar-daily.md --max-tokens 2200`
- `python xpost.py radar-weekly --output /tmp/gitxpost-radar-weekly.md --max-tokens 2600`

实际结果：
- `radar-daily` 成功生成 `/tmp/gitxpost-radar-daily.md`
- `radar-weekly` 成功生成 `/tmp/gitxpost-radar-weekly.md`
- 两条命令都返回 `ok=true`
- 两条命令都成功追加了 `actions.json`
- 使用模型：`claude-opus-4-6`

当前边界：
- 分发层（Telegram / OpenClaw cron）仍未并入 repo 内 CLI
- `interests.json` 目前若不存在会自动创建空模板，但后续仍建议由用户维护真实画像
- 周报对 `topic_trend` 的价值仍依赖连续多周快照积累

日期：2026-03-12

## 本次补充：开源第二轮整理

范围：
- 目录结构重命名与收口
- 历史 skill / plugin 资产分层
- 文档入口与测试素材路径更新

### 1. 内容目录重构

涉及文件：
- `content/`
- `xpost.py`
- `scripts/agent_example.py`
- `CI/`
- `README.md`

变更：
- 将 `CreateMd/` 重构为 `content/`
- 统一形成 `content/template.md`、`content/prompt-guide.md`、`content/prompts/`、`content/examples/`、`content/drafts/`
- `xpost` CLI、示例脚本、CI 测试素材路径切到新结构

效果：
- 仓库结构更适合 GitHub 开源
- 示例、模板、草稿工作区职责更清楚

### 2. Article 工具目录重构

涉及文件：
- `article_tooling/`
- `auto_publish_uc.py`
- `xpost.py`

变更：
- 将 `pasreMarkDown/` 重构为 `article_tooling/`
- 将运行脚本上收为 `article_tooling/scripts/`
- 代码运行路径切到 `article_tooling/scripts/`

效果：
- 去掉历史 typo
- Article 解析与剪贴板脚本的语义更清楚

### 3. skill 关系收口

涉及文件：
- `skills/README.md`
- `docs/skill-topology-2026-03-12.md`

变更：
- repo 顶层只保留 `xpost-cli` 与 `grok-hotposts-cli` 两份活跃 skills
- 历史 `x-article-publisher` skill 与 plugin 的说明统一收敛到文档
- 新增 skill 拓扑文档，明确“保留 / 合并 / 历史参考”的关系

效果：
- skill 层入口更单一
- 历史说明不再以旧 skill / plugin 文件的形式继续保留

### 4. 旧配置清理

涉及文件：
- `config.py`
- `pyEnv.py`

变更：
- 删除未被运行时代码使用的历史配置文件
- 删除旧的 Playwright 环境检测脚本

效果：
- 仓库内不再保留误导性的伪主配置入口

### 本次验证

已验证：
- `python -m py_compile xpost.py auto_publish_uc.py`
- `python xpost.py doctor`
- `python xpost.py init /tmp/gitxpost_v2_cleanup.md --topic 'cleanup pass' --style zara --force`
- `python xpost.py validate /tmp/gitxpost_v2_cleanup.md`

当前边界：
- 示例文件名 `articleNew.md`、`agent_skill_guide.md` 仍可继续优化，但不影响运行

## 本次补充：开源整理后的 smoke 与使用规范文档

范围：
- smoke 回归结果固化
- README 收口
- 使用与忽略规则文档补齐

### 1. smoke 结果入档

涉及文件：
- `CI/report-template.md`

变更：
- 增加“2026-03-12 开源整理后 smoke”真实报告样例
- 记录 `Article` 草稿、`Article` 图片上传、`Post` 纯文本、`Post` 图文、`Grok` JSON 输出的实际结果
- 记录 `Post` 图文一次临时网络错误后重试通过的情况

效果：
- 后续团队做功能验收时，可以直接参考一份真实填写样例

### 2. README 与使用规则收口

涉及文件：
- `README.md`
- `docs/usage-and-ignore-guide-2026-03-12.md`

变更：
- 在 README 中补充最近一次 smoke 通过范围
- 新增使用与忽略规则指南，明确主功能入口、本地运行态目录、应忽略文件、提交前检查顺序
- README 增加对该指南和 `CI/` 的引用

效果：
- 新同事接手时更容易判断怎么用、哪些目录不能误提交

### 3. Markdown 解析器补丁

涉及文件：
- `article_tooling/scripts/parse_markdown.py`

变更：
- 修复 `xpost init --style ...` 生成的 HTML 注释式 prompt 元数据被误解析为标题或正文的问题
- 解析前先剥离 frontmatter 和 HTML 注释

效果：
- `xpost init -> validate -> parse` 重新稳定
- 目录整理后补跑 CLI smoke 时没有再出现标题误识别

### 本次验证

已验证：
- `python xpost.py doctor`
- `python xpost.py init /tmp/gitxpost_smoke_support.md --topic 'support smoke' --style fun --force`
- `python xpost.py validate /tmp/gitxpost_smoke_support.md`
- `python xpost.py parse /tmp/gitxpost_smoke_support.md`
- `python xpost.py post "smoke text after open-source cleanup" --no-wait`
- `python xpost.py post "smoke image after open-source cleanup" --images content/examples/images/demo1.png --no-wait`
- `python grok_hot_posts.py --topics "OpenClaw skills GitHub" --hours 168 --count 5 --json-only`

当前边界：
- Antigravity workflow 仍然依赖外部环境，不在本轮全自动 smoke 范围内

## 本次补充：skills 面向 Codex agent 收口

范围：
- repo 级 skills 重构
- Codex 触发友好性增强

### 1. skills 拆分为三层职责

涉及文件：
- `skills/xpost-cli/SKILL.md`
- `skills/grok-hotposts-cli/SKILL.md`
- `skills/content-workflow/SKILL.md`
- `skills/README.md`
- `docs/skill-topology-2026-03-12.md`

变更：
- 保留 `xpost-cli` 作为执行与发布入口
- 保留 `grok-hotposts-cli` 作为热点搜索入口
- 新增 `content-workflow`，承接 Markdown 起稿、Prompt 选择、Antigravity 配图和发布前准备

效果：
- Codex agent 更容易区分“写内容”“发内容”“搜热点”
- 减少 skill 触发时的职责重叠

### 2. 为 Codex 补充 skill 元数据

涉及文件：
- `skills/xpost-cli/agents/openai.yaml`
- `skills/grok-hotposts-cli/agents/openai.yaml`
- `skills/content-workflow/agents/openai.yaml`

变更：
- 为 3 个活跃 skill 增加 `display_name`、`short_description`、`default_prompt`

效果：
- 后续接入 Codex agent 时，skills 更容易展示和理解

### 3. 旧 skill 说明改写为 Codex 友好格式

变更：
- 移除过长、偏旧工具语境的 skill 说明
- 改为当前 repo 命令、当前目录结构、当前运行习惯

效果：
- 新 skill 文档更短、更聚焦、更贴近当前项目的真实用法

## 本次补充：README、结构审计与开源整理

范围：
- README 与开源说明
- 结构审计与整理清单
- `xpost` CLI 配套收口
- skills 与安装文档收口

### 1. README 与结构审计更新

涉及文件：
- `README.md`
- `docs/repo-structure-audit-2026-03-12.md`
- `docs/supporting-capabilities-audit-2026-03-12.md`
- `docs/open-source-cleanup-checklist-2026-03-12.md`

变更：
- 重写 README，覆盖 Article、Post、Grok、Markdown 创作、Prompt、Antigravity workflow、skills、CI、changelog 规则
- 新增仓库结构审计文档，明确哪些目录合理、哪些属于历史命名
- 新增支撑能力审计文档，复核 Markdown、Prompt、workflow、CLI、skills 这些非主链路能力
- 新增开源整理清单，按“立即做 / 后续做 / 不建议动”分组

效果：
- 项目主文档更接近 GitHub 开源可读状态
- 后续整理优先级已经有统一清单

### 2. CLI 配套和依赖定义收口

涉及文件：
- `xpost.py`
- `requirements.txt`
- `pyproject.toml`
- `scripts/install_cli.sh`

变更：
- `xpost` 顶层描述更新为 gitxPost 统一 CLI，不再只描述 Article
- `doctor` 改为检查当前真实依赖：`patchright`、`Pillow`、剪贴板支持
- `requirements.txt` 与 `pyproject.toml` 去掉已不再使用的旧依赖
- `install_cli.sh` 统一改为 `.venv`
- `xpost init` 现在会自动复制示例 `cover.png` 与 `demo1.png`，使新建文章后可直接通过 `validate`

效果：
- `xpost doctor` 不再误报旧依赖缺失
- 新用户按 README 安装和初始化时，第一步体验更顺

### 3. skills 文案对齐

涉及文件：
- `skills/xpost-cli/SKILL.md`
- `skills/grok-hotposts-cli/SKILL.md`

变更：
- `xpost-cli` skill 补充了 `post`、`post-login`
- skills 里的环境路径统一改为 `.venv`
- `grok-hotposts-cli` 改为优先说明 `--json-only` 直出 JSON 的当前主路径

效果：
- Agent 层的调用说明和当前 CLI 实现一致

### 本次验证

已验证：
- `python xpost.py doctor`
- `python xpost.py init /tmp/gitxpost_readme_audit3.md --topic 'cleanup audit' --style fun --force`
- `python xpost.py validate /tmp/gitxpost_readme_audit3.md`
- `python xpost.py parse content/examples/articleNew.md`
- `python xpost.py --help`
- `python xpost.py publish --help`
- `python xpost.py post --help`

当前边界：
- Antigravity workflow 仍依赖外部运行环境，当前仓库内无法独立全自动验收
- `content/`、`article_tooling/` 仍是历史命名，当前只完成文档收口，尚未做目录重构

范围：
- Article：`undetected-chromedriver` 迁移到共享 CDP 会话层
- Grok：`undetected-chromedriver` 迁移到共享 CDP 会话层
- Post：回归验证，确保迁移不误伤既有能力

## 本次完成的核心变更

### 1. 新的共享浏览器会话层稳定化

涉及文件：
- `browser_cdp_session.py`

变更：
- 移除过严的 asyncio 预检测，避免 OpenClaw 环境误杀 Playwright Sync API
- 保留兼容重试逻辑，减少宿主环境事件循环污染带来的启动失败
- 修复 `create_session()` 已启动后，业务层再次 `session.start()` 的重复启动问题
- 新增任务页创建逻辑，避免默认复用 `pages[0]` 导致脚本落到脏页面
- 默认使用可见 Chrome，会在发现旧的 headless CDP 会话时清理并重启

效果：
- Article、Grok、Post 三条链路统一复用真实 Chrome profile
- Chrome 自动更新不再依赖 chromedriver 精确匹配

### 2. Article 链路迁移完成

涉及文件：
- `auto_publish_uc.py`

变更：
- 改为使用共享会话层创建浏览器和任务页
- 修复登录检查顺序：先校验登录态，再进入 `x.com/compose/articles`
- 修复标题输入：命中当前 Article 编辑器的真实标题 `textarea`
- 修复正文粘贴：优先命中 `data-testid="composer"` 的正文编辑器
- 修复封面上传：通过 `fileInput` 上传并点击 `Apply`
- 修复内容图插入后的成功判定，避免误报“可能失败”
- 补齐 Article 发布按钮选择器，兼容当前页面中的 `Publish` 按钮

效果：
- Article 草稿链路真实跑通
- Article 带内容图、封面图草稿链路真实跑通

### 3. Grok 链路迁移完成

涉及文件：
- `grok_hot_posts.py`

变更：
- 改为使用共享会话层创建浏览器和任务页
- 去掉重复 `session.start()` 调用
- 修复 Grok 回复 JSON 解析后的数值归一化
- 兼容 `N/A`、`1.2K`、`12,345` 这类指标格式

效果：
- Grok 能真实拿到结构化 JSON 输出
- 不再因为 `int("N/A")` 这类错误直接失败

### 4. Post 回归保护

涉及文件：
- `auto_publish_post.py`

变更：
- 接入共享会话层的新任务页创建逻辑
- 明确使用可见 Chrome，会话行为和 Article/Grok 保持一致

效果：
- 已跑通的 Post 纯文本草稿链路未被迁移误伤

## 这次解决了哪些问题

### 问题 1：OpenClaw 环境里所有 Playwright Sync API 都报 asyncio 错误

现象：
- 脚本一启动就报“检测到 asyncio 环境”
- Article 和 Grok 都无法进入真实测试

原因：
- `browser_cdp_session.py` 中人为加了过严的 asyncio 检测
- 宿主环境的事件循环污染被当成了真实不可运行条件

解决：
- 去掉主动拦截
- 改成“先正常启动，必要时做一次兼容重试”

下次怎么处理：
- 这类问题优先做最小可运行验证，不要先在业务层自己封死运行路径
- 先验证“独立子进程 + 最小 sync_playwright().start()”是否真的不能跑

### 问题 2：迁移后业务层重复 `session.start()`，会话被二次启动

现象：
- 浏览器启动异常
- 会话对象状态混乱

原因：
- `create_session()` 内部已经做了 `session.start()`
- 业务层又手动再调了一次

解决：
- 统一约定：`create_session()` 返回的对象已经可用
- 业务层只读 `session.browser / session.context / session.page`

下次怎么处理：
- 共享层如果提供“便捷构造函数”，要明确写清“是否已启动”
- 业务层不要同时混用“工厂函数”和“手动 start 生命周期”

### 问题 3：Article 明明打开了 Articles 页面，后面却一直在错页上操作

现象：
- 标题框找不到
- 正文区找不到
- 实际脚本跑在 `/home` 或别的脏页面

原因：
- 先 `goto(ARTICLES_URL)`，又在 `check_login_status()` 里把同一页导航回 `/home`
- 共享层又默认复用 `pages[0]`，很容易拿到旧页面

解决：
- 先检查登录，再进目标业务页
- 共享层默认创建新的任务页，不再盲目复用 `pages[0]`

下次怎么处理：
- 登录校验不要破坏当前业务页
- 任何复用浏览器的自动化，页面选择都要显式设计

### 问题 4：旧的 headless CDP 会话被静默复用，导致脚本看起来“没反应”

现象：
- 浏览器不可见
- 实际跑在后台 headless Chrome

原因：
- 会话层默认 `headless=True`
- 端口占用时只看“能不能连上”，不看连接的是不是旧的 headless 浏览器

解决：
- 默认改为可见 Chrome
- 检测到端口上是 headless 浏览器时，清理后重启可见会话

下次怎么处理：
- 复用 CDP 端口时，除了“端口可用”，还要校验浏览器模式是否符合当前任务

### 问题 5：Grok 拿到回复了，但结构化输出还是失败

现象：
- 日志显示回复完成
- 最终仍然报 `invalid literal for int() with base 10: 'N/A'`

原因：
- 排序阶段直接对字符串指标做 `int()`
- 实际返回的 `views/likes/reposts` 可能是 `N/A`、`1.2K`

解决：
- 新增统一数值归一化函数
- 排序和输出前先转成稳定整数

下次怎么处理：
- LLM 返回的结构化数据不能假设字段类型永远干净
- 排序、比较前要先做 normalize

## 当前真实状态

已实测通过：
- Article 草稿
- Article 带图草稿
- Grok JSON 输出
- Post 纯文本草稿回归

已实测通过：
- Article 真发布

补充说明：
- Article 发布最终采用“两步发布”处理
- 第一步：编辑页右上角 `Publish`
- 第二步：`Publish Article` 确认层中的 `Publish`
- 已在 `Published` 列表中回查到标题 `macOS 效率革命：我如何利用 AI 构建专属的语音输入法`

## 本次补充：澄清 Article 生成闭环预期

范围：
- README 与团队使用文档
- Article 最小闭环操作说明

### 1. 澄清 `xpost init` 的真实职责

涉及文件：
- `README.md`
- `docs/usage-and-ignore-guide-2026-03-12.md`

变更：
- 明确 `xpost init` 只生成 Markdown 骨架，不会直接写出完整正文
- 明确 `--style` 的作用是写入 Prompt 元数据，供 Claude / OpenClaw / Codex 后续生成正式文章
- 明确 `validate` 与 `parse` 只负责结构检查与解析，不负责写正文

效果：
- 减少同事把“骨架生成”误认为“成文生成”的预期偏差
- 团队更容易理解最小闭环里外部 LLM 的必要位置

### 2. 新增最小闭环 runbook

涉及文件：
- `docs/article-minimal-loop-runbook-2026-03-13.md`

变更：
- 新增一份团队操作说明
- 用固定顺序说明：主题/风格 -> 骨架 -> 外部 LLM 生成正文 -> Antigravity 配图 -> 校验 -> 草稿 -> 正式发布
- 补充给 Claude / OpenClaw / Codex 的推荐指令模板

效果：
- 新同事可以直接按 runbook 走通文章生产最小闭环
- 项目边界和协作方式更清楚

## 本次补充：补齐 LLM 成文与 X 雷达 CLI

范围：
- `xpost` CLI 能直接把文章骨架生成成正式 Markdown
- `xInfo` 迁入仓库并接入统一 CLI

### 1. 新增 Article 成文生成命令

涉及文件：
- `xpost.py`
- `README.md`
- `docs/usage-and-ignore-guide-2026-03-12.md`
- `skills/xpost-cli/SKILL.md`
- `skills/content-workflow/SKILL.md`

变更：
- 新增 `xpost generate <md_path>`
- 支持从 `xpost init` 生成的嵌入 Prompt 中提取风格和主题
- 支持直接调用本地 LLM messages API 生成完整 Markdown 正文
- 默认优先读取 `XPOST_LLM_API_*` 环境变量；旧版曾支持本地 TokenMax 配置回退
- 写回文章前自动生成 `*.skeleton.<timestamp>.md` 备份
- 生成完成后自动做一次 `validate`，并检查模板占位句子是否仍残留

效果：
- `topic/style -> 骨架 -> 成文 -> 配图 -> 发布` 现在可以在 `xpost` CLI 中闭环
- 同事不必再手动复制 Prompt 才能从骨架变成正文

### 2. 迁入 X 雷达并统一 CLI 入口

涉及文件：
- `xinfo/README.md`
- `xinfo/x_ideas_scan.py`
- `xinfo/analyze_network.py`
- `xinfo/manage_accounts.py`
- `xpost.py`
- `.gitignore`

变更：
- 将 `xInfo` 的核心扫描、分析、账号管理脚本迁入 `gitxPost/xinfo/`
- 新增统一 CLI：
  - `xpost radar-scan`
  - `xpost radar-analyze`
  - `xpost radar-accounts`
- 为 `xinfo/log/` 与 `xinfo/RESULT.json` 补充忽略规则
- 去掉 `x_ideas_scan.py` 中遗留的调试打印

效果：
- X 雷达能力不再需要切回旧项目执行
- `gitxPost` 现在统一承接 Article、Post、Grok、Radar 四类能力

### 3. 验收用例补充

涉及文件：
- `CI/test-cases.md`
- `CI/report-template.md`

变更：
- 新增 `TC-00 Article 成文生成`
- 新增 `TC-08 Radar 扫描`
- 新增 `TC-09 Radar 分析`

效果：
- 新增功能后有明确的回归入口，不会只靠手工记忆验收

### 本次验证

已验证：
- `python -m py_compile xpost.py xinfo/x_ideas_scan.py xinfo/analyze_network.py xinfo/manage_accounts.py`
- `python xpost.py --help`
- `python xpost.py generate --help`
- `python xpost.py radar-analyze --help`
- `python xpost.py radar-accounts list`
- `python xpost.py init /tmp/gitxpost_generate_smoke.md --topic "OpenClaw ACP 为什么能替代我自建的 tmux worker" --style zara --force`
- `python xpost.py generate /private/tmp/gitxpost_generate_smoke.md --model claude-sonnet-4-6 --max-tokens 2200`
- `python xpost.py radar-scan`
- `python xpost.py radar-analyze --days 7`

当前边界：
- `xpost generate` 依赖可用的本地 LLM API 配置；若上游服务暂时不可用，会直接返回错误
- `radar-scan` 的成功率仍受外部 RSS/Nitter 实例状态影响

### 4. 收口 X 相关 skills，并改为中文触发文案

涉及文件：
- `skills/xpost-cli/SKILL.md`
- `skills/xpost-cli/agents/openai.yaml`
- `skills/x-radar-cli/SKILL.md`
- `skills/x-radar-cli/agents/openai.yaml`
- `skills/grok-hotposts-cli/SKILL.md`
- `skills/content-workflow/SKILL.md`
- `skills/README.md`
- `docs/skill-topology-2026-03-12.md`
- `docs/supporting-capabilities-audit-2026-03-12.md`
- `README.md`

变更：
- 将 `xpost-cli` 的职责收窄为 Article / Post / doctor / generate 等内容发布命令
- 新增 `x-radar-cli`，专门承接 `radar-scan`、`radar-analyze`、`radar-daily`、`radar-weekly`、`radar-accounts`
- 将 4 个活跃 `SKILL.md` 的 frontmatter 描述与正文统一改为中文，仅保留标题层级为英文
- 同步调整 skill 拓扑文档与 README，明确各 skill 的触发边界

效果：
- OpenClaw / Codex 在中文语境下更容易匹配到正确 skill
- 内容发布与雷达情报两类任务不再争抢同一个 skill 触发入口
