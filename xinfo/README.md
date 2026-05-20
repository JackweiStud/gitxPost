# 🦞 X 创意雷达系统

> 每天自动抓取 X 推文 → AI 个性化筛选 → 推送精选日报 + 每周网络分析

**项目状态**: ✅ 生产运行中  
**最后更新**: 2026-03-04

---

## 📦 项目结构

```
gitxPost/xinfo/
├── x_ideas_scan.py         # 🔍 扫描引擎：RSS 抓取 + 持久化日志 + RESULT JSON
├── analyze_network.py      # 📊 分析引擎：人脉发现 + 热点追踪 + 趋势时间序列
├── manage_accounts.py      # 🛠️ 账号管理 CLI：add/remove/restore/list
├── doc/
│   ├── X_RADAR_DOCS.md     # 📖 技术文档：架构决策 + 部署指南 + FAQ
│   └── learn.md            # 📝 数据使用策略与实操指南
└── log/
    ├── ideas.md            # 推文内容归档（保留最近 5 天）
    ├── .ideas_seen.json    # 结构化记录：每条 URL 带 source / type / seen_at
    ├── interests.json      # ⭐ 个人兴趣画像（AI 筛选依据，可随时编辑）
    ├── actions.json        # 📋 行动追踪（AI 自动写入，手动更新 status）
    ├── day/                # 天级结果：.log / _result.json / _analysis.json / .md
    ├── week/               # 周报正文归档：YYYY-MM-DD.md
    ├── trends/             # 热点趋势周快照：YYYY-WW.json（用于趋势对比）
    └── account_backups/    # manage_accounts.py 每次修改前的自动备份
```

---

## 🚀 快速开始

### 1. 扫描推文（获取数据）

推荐在当前仓库中直接使用统一 CLI：

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate
python xpost.py radar-scan
```

输出 `RESULT JSON`，包含扫描统计 + `new_ideas_preview`（今日精选预览）。  
同时写入 `log/ideas.md`、`log/.ideas_seen.json`、`log/day/YYYY-MM-DD.log`。

结果文件说明：

- `RESULT.json`
  - 最新一次扫描快照
  - 每次运行覆盖，不按天保留
- `log/day/YYYY-MM-DD.log`
  - 天级扫描日志
- `log/day/YYYY-MM-DD_result.json`
  - 天级扫描结果快照
- `log/day/YYYY-MM-DD_analysis.json`
  - 天级分析结果
- `log/day/YYYY-MM-DD.md`
  - 天级日报正文
- `log/week/YYYY-MM-DD.md`
  - 周报正文归档
- `log/trends/YYYY-WW.json`
  - 周级趋势快照
- `log/ideas.md`
  - 滚动内容归档，不是严格按天拆分
- `log/.ideas_seen.json`
  - 去重与历史记录索引，不是按天拆分

### 2. 分析洞察（获取价值）

```bash
# 统一 CLI
python xpost.py radar-analyze --days 7

# 直接脚本模式（兼容旧用法）
python xinfo/analyze_network.py 7 --json
```

`--json` 模式自动保存 `log/day/YYYY-MM-DD_analysis.json` 和 `log/trends/YYYY-WW.json`（热点趋势周快照）。

### 2.1 生成日报

```bash
python xpost.py radar-daily
```

默认行为：

- 读取 `RESULT.json`
- 读取 `log/interests.json`
- 生成 `log/day/YYYY-MM-DD.md`
- 追加 `log/actions.json`
- 默认使用 TokenMax Opus（`claude-opus-4-6`）

补充说明：

- `log/interests.json` 是雷达日报 / 周报筛选标准的核心文件
- 如果这份文件还是默认空模板，日报虽然能生成，但筛选会不够个性化
- 建议先同步或维护真实的兴趣画像，再运行日报 / 周报

### 2.2 生成周报

```bash
python xpost.py radar-weekly
```

默认行为：

- 读取 `log/day/YYYY-MM-DD_analysis.json`
- 读取 `log/actions.json`
- 生成 `log/week/YYYY-MM-DD.md`
- 可继续追加 `log/actions.json`
- 默认使用 TokenMax Opus（`claude-opus-4-6`）

运行日志：

- `radar-daily` 每次运行会追加写入 `log/runtime/YYYY-MM-DD_radar-daily.jsonl`
- `radar-weekly` 每次运行会追加写入 `log/runtime/YYYY-MM-DD_radar-weekly.jsonl`
- 日志中包含输入文件、模型、尝试记录、错误信息和原始响应摘要，适合排查 “LLM 未返回 markdown” 这类问题

### 3. 管理监控账号

```bash
# 查看所有活跃账号
python xpost.py radar-accounts list

# 添加新账号
python xpost.py radar-accounts add QuiverAI "AI数据分析，多方推荐"

# 移除账号（注释保留，可恢复）
python xpost.py radar-accounts remove elvissun

# 恢复已注释账号
python xpost.py radar-accounts restore elvissun
```

> 每次操作前自动备份到 `log/account_backups/`，保留最近 10 份。

### 4. 同步 Following 与 Radar 差异

```bash
python xpost.py following-sync jackaiwison
```

该命令复用 `chrome_data_mirror` 的 X 登录态，通过页面 DOM 与 Following GraphQL 响应双通道抓取 `@jackaiwison` 当前 Following 列表，并和 `accounts.json` 中 `status=active` 的 Radar 账号对比。

输出：

- `xinfo/log/following/YYYY-MM-DD.json`：当天 Following 原始快照与对比结果
- `xinfo/log/following/myfollowing_latest.json`：最新快照
- `xinfo/log/myfollowing.xlsx`：五个标签页报表

`myfollowing.xlsx` 的标签页：

- `Summary`：抓取时间、Following 数量、Radar 数量、GAP 统计、完整性状态
- `Following`：X 当前关注列表
- `Radar`：当前活跃 Radar 账号
- `GAP1_Following_Not_Radar`：Following 有但 Radar 没有，适合找新增候选
- `GAP2_Radar_Not_Following`：Radar 有但 Following 没有，适合找移除候选

完整性字段：

- `completion_status=complete`：采集数量达到 X profile 显示的 Following 数量。
- `completion_status=partial`：未收满，通常是滚动/页面加载提前停止。
- `completion_status=partial_limited`：使用了 `--limit`，结果只适合 smoke test。
- `completion_status=unknown`：未能读取预期 Following 总数，不应视为完整快照。

### 5. 更新个人兴趣画像

直接编辑 `log/interests.json`，AI 日报筛选标准立即更新，无需改任何代码：

```json
{
  "focus": ["multi-agent", "OpenClaw 生态与相关插件"],
  "recent_context": ["关注 agent、openclaw 的 skill、记忆"],
  "ignore": ["纯 meme", "NFT 炒作", "政治内容"]
}
```

---

## ✅ 核心能力

| 能力 | 说明 | 状态 |
|------|------|:----:|
| **RSS 抓取** | 零封号风险，多实例自动 Fallback | ✅ |
| **结构化去重** | seen.json 记录 source / type / author / seen_at | ✅ |
| **持久化日志** | 每日运行日志 `log/day/YYYY-MM-DD.log` | ✅ |
| **RESULT JSON** | 机器可读扫描结果 + `new_ideas_preview` 精选（MAX 3/账号） | ✅ |
| **兴趣画像驱动** | `interests.json` 动态定义筛选标准 | ✅ |
| **二度人脉发现** | 通过 RT 关系自动推荐新账号 | ✅ |
| **热点话题提取** | 停用词过滤后的有效关键词，中英文 | ✅ |
| **热点趋势时间序列** | 周快照对比，输出 📈上升/📉下降/🆕首现 | ✅ |
| **亮点推文提取** | 按关键词密度评分，`top_posts` 字段 | ✅ |
| **账号质量分析** | 原创率、RT 比、回复率 | ✅ |
| **账号一键管理** | `manage_accounts.py` add/remove/restore | ✅ |
| **Action Tracker** | 日报 📌 自动写入 `actions.json`，周报回顾进度 | ✅ |

---

## 🗓️ Cron 任务

| 任务 | 时间 | 内容 |
|------|------|------|
| `x-radar-daily` | 每天 07:00 | 扫描 → AI 读 interests.json → 筛选 → Telegram 日报 → 写 actions.json |
| `x-radar-weekly` | 每周日 21:00 | analyze_network.py → 热点趋势/二度人脉/亮点推文/账号建议/行动回顾 |

---

## 📋 数据使用策略

| 数据 | 消费者 | 频率 | 用途 |
|------|:----:|:----:|------|
| **RESULT JSON** | Cron `x-radar-daily` | 每天 07:00 | AI 从 `new_ideas_preview` 筛选：🔧工具 / 🧠洞察 / 💰机会 / 📌行动 |
| **interests.json** | 日报 Agent（步骤0读取） | 随时可改 | 动态定义筛选标准 |
| **actions.json** | 日报写入 / 周报回顾 | 日报自动追加 | 行动追踪闭环 |
| **trends/*.json** | 周报 Agent | 每周积累 | 热点话题趋势对比（第2周起生效） |
| **.ideas_seen.json** | `analyze_network.py` | 按需 | 二度人脉发现 + 账号质量统计 |

---

## 🔧 运维

```bash
# 查看今日日志
cat xinfo/log/day/$(date +%Y-%m-%d).log

# 查看行动追踪
cat xinfo/log/actions.json | python3 -m json.tool

# 查看热点趋势快照
ls xinfo/log/trends/

# 验证账号数量
python xpost.py radar-accounts list
```

### 故障排查

| 问题 | 解决 |
|------|------|
| 所有账号失败 | `curl -I https://nitter.net/用户名/rss` 测试，添加新实例 |
| 某账号持续失败 | `python xpost.py radar-accounts remove 账号`，下次运行自动跳过 |
| ideas.md 为空 | 检查 `log/day/` 日志中的错误信息 |
| 亮点推文为空 | 检查 ideas.md 是否有数据，运行 `analyze_network.py 7 --json` 重新生成 |

---

## 📈 技术演进

| 版本 | 方案 | 结果 | 原因 |
|------|------|:----:|------|
| v1 | nitter 直接请求 | ❌ | VPS IP 被封 |
| v2 | Camoufox 浏览器 | ❌ | 内存泄漏（51 分钟） |
| v3 | 纯 RSS + 多实例 | ✅ | 稳定、轻量（3 秒/账号） |
| v3.5 | + 结构化分析 + AI Cron Agent | ✅ | AI 替代规则脚本做内容筛选 |
| v4.0 | + interests.json + Action Tracker + 趋势时间序列 | ✅ | 个性化 + 闭环追踪 |

---

**维护者**: openclaw_multiagent_researcher  
**可用性**: 生产使用中 🚀
