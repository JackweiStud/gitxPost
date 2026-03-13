# Radar 日报/周报并入 gitxPost 的迁移设计

日期：2026-03-13

## 1. 背景

当前 `gitxPost` 已经具备：

- `Article`：长文起稿、成文、校验、发布
- `Post`：短帖发布
- `Grok`：热点搜索
- `Radar` 基础能力：
  - `xpost radar-scan`
  - `xpost radar-analyze`
  - `xpost radar-accounts`

但你在 OpenClaw cron 中使用的“X 创意雷达日报任务”和“周报任务”已经比当前 `Radar` CLI 更进一步。它们不只是“扫数据”，而是已经形成完整闭环：

日报链路：

1. 读取兴趣画像
2. 扫描 X 数据
3. 从真实结果中筛选
4. 生成中文日报
5. 发送 Telegram
6. 写入行动追踪
7. 保存本地日报归档

周报链路：

1. 运行分析脚本
2. 读取当天分析结果
3. 读取行动追踪
4. 生成周报正文与账号建议
5. 分两段发送 Telegram

所以这次迁移设计的目标，不是重写现有扫描器，而是把这两条“情报生产链路”系统化并入 `gitxPost`。

---

## 2. 迁移目标

目标：

- 把 OpenClaw cron 里的 Radar 日报/周报流程沉淀为 `gitxPost` 的正式能力
- 让日报与周报生产依赖 repo 内明确的数据契约，而不是散落在 cron prompt 里的隐式规则
- 保留“严格禁止编造”的约束
- 保留个性化兴趣画像与 Action Tracker 机制
- 后续既能给 OpenClaw cron 用，也能给 Claude / Codex / 其他 agent 用

非目标：

- 本阶段不重写 RSS 扫描器
- 本阶段不替换 Telegram 通道
- 本阶段不改成完全异步架构
- 本阶段不做多租户、多用户画像

---

## 3. 当前可复用资产

已经在 repo 中的可复用能力：

- `xinfo/x_ideas_scan.py`
  - 扫描并产出 `RESULT.json`
- `xinfo/analyze_network.py`
  - 结构化分析、趋势和热点
- `xinfo/manage_accounts.py`
  - 账号管理
- `xinfo/log/interests.json`
  - 兴趣画像入口（目前文档已约定，但运行数据仍属于本地运行态）
- `xinfo/log/actions.json`
  - 行动追踪数据容器（同上）
- 天级与周级结果目录：
  - `xinfo/log/day/`
  - `xinfo/log/trends/`

已经明确的业务规则：

- 只能使用真实扫描结果，不允许补写不存在的推文
- 筛选标准以 `interests.json` 为唯一依据
- 行动建议要落入 `actions.json`
- 日报需要本地归档

这些资产说明：Radar 日报/周报并不是从零开始，而是已经有 70% 的数据底座。

---

## 4. 两种迁移方案对比

### 方案 A：继续把所有业务逻辑放在 OpenClaw cron prompt 中

特点：

- repo 只负责扫描与分析
- 日报筛选、写作、发送、归档仍由 cron prompt 驱动

优点：

- 改动最小
- 不需要新增 repo 内命令

缺点：

- 规则散落在 cron 文本里，不容易复用
- Claude / Codex / OpenClaw 以外的调用方难以共享
- 规则一多，就会出现“提示词漂移”和维护困难

### 方案 B：在 `gitxPost` 中增加“情报生产层”，cron 只负责调度

特点：

- repo 内提供正式的数据输入输出约定
- cron 只负责调用和分发

优点：

- 规则沉淀在项目中，易维护
- 易于给 OpenClaw、Claude、Codex 共用
- 验收口径更清晰

缺点：

- 需要补一层设计和文档
- 需要明确输入输出契约

### 方案 C：把日报直接做成单体大命令，扫描、筛选、写作、发送全打包

优点：

- 使用简单，一条命令跑完

缺点：

- 耦合过高
- 一旦某一层出问题，很难定位
- 不利于测试与复用

### 推荐结论

推荐采用 **方案 B**。

原因：

- 它最适合现在项目的状态
- 保留了现有 `radar-scan` / `radar-analyze` 资产
- 又能把日报/周报逻辑正式沉淀进 repo
- 不会把“发送 Telegram”这种通道逻辑过早写死在核心层

---

## 5. 推荐架构

推荐把 Radar 体系分成三层：

### 第一层：数据采集层

已有：

- `xpost radar-scan`
- `xpost radar-analyze`
- `xpost radar-accounts`

职责：

- 获取真实原始数据
- 生成可复用的结构化结果
- 形成天级与周级归档

### 第二层：情报生产层

建议新增的逻辑层，不一定一开始就写成代码命令，但要先定义清楚：

日报部分：

- 读取 `interests.json`
- 读取 `RESULT.json`
- 如果无新内容，输出“今日暂无新推文”
- 如果有新内容，按兴趣画像筛选
- 生成“热议话题 + 分类日报 + 行动建议”
- 更新 `actions.json`
- 写入 `xinfo/log/day/YYYY-MM-DD.md`

周报部分：

- 读取 `xinfo/log/day/YYYY-MM-DD_analysis.json`
- 读取 `actions.json`
- 基于 `hot_topics.keywords` 做语义聚类，生成本周热点话题 Top5
- 从 `network.items` 提取二度人脉推荐
- 从 `top_posts.items` 提取亮点推文
- 汇总 pending 行动与本周新增行动
- 基于 `account_stats` 产出账号调整建议
- 输出周报正文与第二段行动/账号建议

这是这次迁移设计的核心。

### 第三层：分发层

建议保持独立，不写死在数据生产层中：

- Telegram
- OpenClaw cron
- 其他通知通道

职责：

- 拿日报 Markdown 文本去发送
- 不负责判断和筛选

这样做的好处是：

- 数据、内容、分发三层解耦
- 后续要换 Telegram、Slack、邮件，不影响日报生成逻辑

---

## 5.1 推荐 cron 执行顺序

为了避免“扫描结果是新的，但分析结果还是旧的”这种状态，建议把 cron 固定成下面这套顺序。

### 每日日报任务

推荐顺序：

1. 运行扫描
   - `python xpost.py radar-scan`
2. 运行分析
   - `python xpost.py radar-analyze --days 7`
3. 生成日报 Markdown
   - `python xpost.py radar-daily`
4. 发送日报
   - 由 OpenClaw cron / Telegram 通道读取 `xinfo/log/day/YYYY-MM-DD.md` 发送

可直接抄用的顺序说明：

- `radar-scan` 负责更新 `RESULT.json` 和 `day/YYYY-MM-DD_result.json`
- `radar-analyze --days 7` 负责更新 `day/YYYY-MM-DD_analysis.json`
- `radar-daily` 只读真实扫描结果和兴趣画像，产出日报正文与新增行动
- 发送层不要直接读命令 stdout，统一读落地文件

### 每周周报任务

推荐顺序：

1. 运行分析
   - `python xpost.py radar-analyze --days 7`
2. 生成周报 Markdown
   - `python xpost.py radar-weekly`
3. 发送周报
   - 由 OpenClaw cron / Telegram 通道读取 `xinfo/log/week/YYYY-MM-DD.md` 发送

可直接抄用的顺序说明：

- 周报不要直接依赖上次遗留的 `*_analysis.json`
- 周报生成前先跑一次 `radar-analyze --days 7`，确保使用的是当前滚动 7 天分析结果
- 周报正文归档固定写入 `xinfo/log/week/YYYY-MM-DD.md`
- `trends/YYYY-WW.json` 仅作为趋势对比辅助输入，不作为周报正文归档

---

## 6. 建议补齐的数据契约

为了让日报生产层稳定，建议明确下面几份文件的角色。

### 6.1 `xinfo/log/interests.json`

角色：

- 日报筛选的唯一输入规则

建议字段：

- `focus`
- `recent_context`
- `ignore`
- 可选：`priority_accounts`
- 可选：`categories`

建议保持简单，不做复杂 DSL。

### 6.2 `xinfo/RESULT.json`

角色：

- 最新扫描结果快照
- 供日报生产层直接读取

关键依赖字段：

- `summary.status`
- `summary.new_ideas_preview`
- `failed_accounts`
- `successful_accounts`

### 6.3 `xinfo/log/day/YYYY-MM-DD_analysis.json`

角色：

- 周报生产层的主输入

当前生产者：

- `python xpost.py radar-analyze --days 7`
- 或兼容旧用法：`python xinfo/analyze_network.py 7 --json`

关键依赖字段：

- `hot_topics.keywords`
- `topic_trend`
- `network.items`
- `top_posts.items`
- `account_stats.items`

注意：

- 周报应优先读取“当天的分析结果文件”，而不是依赖 stdout
- 这是当前 OpenClaw 周报 cron 最值得保留的设计点
- 这个文件不是 `radar-scan` 自动生成的，而是 `radar-analyze` 在 `--json` 模式下写出的

这意味着：

- 如果每天只跑“日报任务”，且日报任务只执行 `radar-scan`
- 那么 `YYYY-MM-DD_analysis.json` 不会自动刷新

因此推荐二选一：

1. **推荐方案**：每日任务在 `radar-scan` 之后顺手执行一次 `radar-analyze --days 7`
   - 好处：每天都会沉淀一份当天分析结果
   - 周报可以直接读取最近一天的分析文件
2. **保守方案**：周报任务在生成前先执行一次 `radar-analyze --days 7`
   - 好处：改动最小
   - 缺点：平时不会积累每天的分析快照

本设计更推荐 **方案 1**，因为它更符合“天级归档”的目标。

### 6.4 `xinfo/log/actions.json`

角色：

- 行动建议的持久化追踪

建议最小结构：

```json
{
  "actions": [
    {
      "action": "具体行动",
      "date": "2026-03-13",
      "status": "pending",
      "source_link": "https://x.com/...",
      "source_account": "@someone"
    }
  ]
}
```

### 6.5 `xinfo/log/day/YYYY-MM-DD.md`

角色：

- 每日日报归档

这份文件应该成为“人类可读的最终结果”，而不是临时日志。

### 6.6 `xinfo/log/week/YYYY-WW.md` 或 `xinfo/log/week/YYYY-MM-DD.md`

建议新增：

- 周报归档文件

推荐两种命名方式二选一：

- `YYYY-WW.md`
  - 强调“自然周”
- `YYYY-MM-DD.md`
  - 强调“本次生成日期”

我更推荐第二种：

- `xinfo/log/week/YYYY-MM-DD.md`

原因：

- 跟现在 `day/YYYY-MM-DD_analysis.json` 的阅读习惯一致
- 避免 `%Y-%W` / ISO week 差异带来的误解
- 更适合回溯“哪天生成了哪份周报”

补充建议：

- 周报文件名用 `YYYY-MM-DD.md`
- 但在文件正文或 frontmatter 里补充：
  - `scope_days: 7`
  - `generated_at: YYYY-MM-DD HH:MM:SS`
  - `source_analysis_file: xinfo/log/day/YYYY-MM-DD_analysis.json`
  - 可选：`scope_week_label: 2026-W11`

这样既保留“生成日期”的可读性，也不会丢掉“它属于哪一周”的语义。

---

## 7. 日报输出建议结构

建议保留你现在 cron prompt 里的整体结构，因为它已经很实用：

1. 日期
2. 今日热议话题
3. `🔧 值得试用的新工具/产品`
4. `🧠 有价值的行业洞察或趋势`
5. `💰 商业机会或变现思路`
6. `📌 可这周实践的具体行动`

约束建议保留：

- 每类最多 8 条
- 全文总数不超过 20 条
- 只允许引用真实 `new_ideas_preview` 条目
- 每条都必须保留来源账号和原文链接
- `ignore` 命中的内容一律跳过

我建议多补一条约束：

- 如果某个分类没有满足条件的条目，允许整个分类缺席，不要为了“版式完整”硬凑

这条会明显减少日报里的低质量噪音。

---

## 8. 周报输出建议结构

建议保留你现在周报 cron 的两段式设计，因为它兼顾可读性和长度控制。

### 第一段：周报正文

建议结构：

1. `📊 X 创意雷达周报 YYYY-MM-DD`
2. `📈 本周热点话题 Top5`
3. `🌐 二度人脉推荐`
4. `💡 本周亮点推文`

建议保留的规则：

- 热点话题不能直接输出原始关键词
- 必须先读取 `hot_topics.keywords` 全量列表，再做语义聚类
- 每个话题应是“可读的话题名 + 一句话描述”
- 如果 `topic_trend.status == ok`，可以标注：
  - `📈`
  - `📉`
  - `🆕`
- 二度人脉推荐只列 `recommended_by_count >= 2`
- 亮点推文最多 5 条，必须保留原始链接

### 第二段：行动 + 账号建议

建议结构：

1. `📋 行动追踪`
2. `🔧 账号调整建议`
3. `✅ 建议保留`
4. `❌ 建议移除`

建议保留的规则：

- `pending` 行动最多 5 条
- 本周新增行动只来自本次分析可推导出的真实建议
- 账号建议必须基于 `account_stats`
- “建议保留”优先选择原创率高、样本量足够的账号
- “建议移除”优先选择原创率低、停更、样本极少的账号
- 不要在末尾附加系统说明文字

### 为什么这套周报结构有价值

这套结构的价值不在“漂亮”，而在于它同时覆盖了：

- 热点
- 网络
- 具体内容
- 行动
- 账号运营

也就是说，它不是单纯的信息摘要，而是已经在做策略辅助。

---

## 9. “严格禁止编造”如何制度化

这部分价值非常高，建议从“提示词规则”提升为“产品规则”。

建议制度化为 4 条：

1. 只能从 `summary.new_ideas_preview` 中选材
2. 每条必须保留原始 `link`
3. 不允许补写不存在的产品名、结论或账号
4. 若信息不足，只允许“省略”，不允许“脑补”

这样做的意义是：

- 日报会更可信
- 后续交给不同 agent 执行，也不容易跑偏
- 便于测试验收

建议未来把它写进：

- README 的 Radar 小节
- Radar 专属 runbook
- 对应 skill 文案

---

## 10. 日报 / 周报使用的 LLM 策略

这两条链路里，真正需要 LLM 的部分不是扫描和分析本身，而是：

- 日报内容整理
- 周报话题聚类、语言润色与结构化输出

推荐模型策略：

- **日报默认模型**：TokenMax `Opus`
- **周报默认模型**：TokenMax `Opus`

推荐优先级：

1. `claude-opus-4-6`
2. `claude-opus-4-5`
3. 仅在 Opus 临时不可用时，再考虑 Sonnet 作为降级

原因：

- 日报和周报都属于“信息压缩 + 分类判断 + 结构化写作”
- 这类任务对模型的摘要稳定性、分类质量、语义聚类能力要求较高
- `Opus` 更适合承担最终的日报/周报成品生成

这里也要明确边界：

- `radar-scan`：不需要 LLM
- `radar-analyze`：不需要 LLM
- 只有“日报生产层”和“周报生产层”使用 TokenMax Opus

这能避免把 LLM 依赖扩大到数据采集层。

---

## 11. 当前趋势快照文件的语义问题

你现在 `radar-analyze --days 7` 会固定写出：

- `xinfo/log/trends/2026-10.json`

这在“技术上”是当前脚本的预期行为，因为它用的是：

- `datetime.now().strftime('%Y-%W')`

所以同一周内会覆盖同一个周快照文件。

这个设计对“周快照”是合理的，但对“每天跑一次 `--days 7` 的滚动分析”不完全严谨，原因是：

- `--days 7` 是滚动窗口，不是自然周
- 同周覆盖会让文件名看起来像“同一口径”，实际内容却可能每天变化

建议在迁移周报时明确这两个层次：

- `day/YYYY-MM-DD_analysis.json`
  - 当天真实分析结果
- `trends/YYYY-WW.json`
  - 周级趋势快照，用于跨周对比

也就是说：

- 周报正文应优先基于当天 `*_analysis.json`
- `trends/*.json` 只作为趋势对比辅助输入

这样语义最清楚。

---

## 12. 建议的未来 CLI 形态

这次不写代码，但建议未来命令设计提前统一。

推荐新增：

- `xpost radar-daily`
- `xpost radar-weekly`

`xpost radar-daily` 职责：

- 读取 `interests.json`
- 读取最新 `RESULT.json`
- 生成日报 Markdown
- 更新 `actions.json`
- 写入 `xinfo/log/day/YYYY-MM-DD.md`

可选参数：

- `--date`
- `--dry-run`
- `--stdout`
- `--write-actions`
- `--write-report`

`xpost radar-weekly` 职责：

- 读取当天 `xinfo/log/day/YYYY-MM-DD_analysis.json`
- 读取 `actions.json`
- 生成“热点 / 人脉 / 亮点 / 行动 / 账号建议”两段式周报
- 写入 `xinfo/log/week/YYYY-MM-DD.md`
- 可选输出 JSON 摘要供分发层使用

可选参数：

- `--date`
- `--analysis-file`
- `--stdout`
- `--write-report`
- `--limit-pending`

分发建议不要一开始并进这个命令。

更稳的方式是：

- `xpost radar-daily` 只产出日报文本和副作用文件
- `xpost radar-weekly` 只产出周报文本和副作用文件
- 发送 Telegram 由 OpenClaw cron 或单独的分发命令处理

---

## 13. 推荐迁移顺序

### Phase 1：规则沉淀

先把这几件事做进 repo：

- 明确 `interests.json` 的结构
- 明确日报输出格式
- 明确 `actions.json` 数据契约
- 明确“不允许编造”的规则

这是最低成本、最高收益的一步。

### Phase 2：日报生产层

新增 repo 内的日报生成逻辑：

- 输入：`RESULT.json + interests.json`
- 输出：日报 Markdown + actions 更新
- 默认用 TokenMax Opus 生成最终日报文本

这一步完成后，OpenClaw cron 就不需要再承担那么长的筛选逻辑。

### Phase 3：周报生产层

新增 repo 内的周报生成逻辑：

- 输入：`YYYY-MM-DD_analysis.json + actions.json`
- 输出：周报 Markdown
- 默认用 TokenMax Opus 生成最终周报文本

这一步完成后，OpenClaw 周报 cron 里的大段业务规则也可以退化成简单调度。

### Phase 4：分发收口

再决定是否补：

- Telegram 分发
- 失败重试
- channel 抽象

建议放最后，因为它和核心价值关系最弱。

---

## 14. 验收标准

迁移完成后，建议用下面标准验收：

### 功能验收

- 能基于当天 `RESULT.json` 生成日报
- 能正确读取 `interests.json`
- 能在 `status = no_new` 时输出“暂无新推文”
- 能把 `📌` 条目写入 `actions.json`
- 能把日报写入 `xinfo/log/day/YYYY-MM-DD.md`
- 能明确记录日报生成所使用的模型与源数据文件
- 能基于当天 `*_analysis.json` 生成周报
- 能基于 `actions.json` 汇总 pending 行动
- 能把周报写入 `xinfo/log/week/YYYY-MM-DD.md`
- 能明确记录周报生成所使用的模型与源分析文件

### 质量验收

- 日报中每条内容都能追溯到原始链接
- 不出现不在 `new_ideas_preview` 中的编造条目
- `ignore` 类内容不会进入日报
- 空分类不会强行填充
- 周报中的热点话题是语义归纳，不是原始关键词堆砌
- 周报中的账号建议可以追溯到 `account_stats`
- 周报中的亮点推文可以追溯到 `top_posts.items`

### 工程验收

- 数据层、日报层、分发层职责清楚
- 数据层、周报层、分发层职责清楚
- 可以在不发送 Telegram 的情况下单独跑日报生成
- 可以在不发送 Telegram 的情况下单独跑周报生成
- README 和 runbook 能指导同事独立使用

---

## 15. 最终建议

这次最值得迁过来的，不是“定时任务本身”，而是它背后的 7 个能力：

1. `interests.json` 兴趣画像
2. 日报内容生成规则
3. `actions.json` 行动闭环
4. 天级 Markdown 归档
5. 严格禁止编造
6. 周报语义聚类与趋势总结
7. 基于 `account_stats` 的账号运营建议

如果把这 7 个能力系统化，`gitxPost` 的 Radar 才会从“能扫数据”升级成“能产出情报”。

最推荐的路线是：

- 先把日报生产层并入 repo
- 再把周报生产层并入 repo
- 最后让 OpenClaw cron 退化成一个纯调度器

这样后续不管是 OpenClaw、Claude、Codex，还是手工 CLI，都能共享同一套 Radar 日报能力。
