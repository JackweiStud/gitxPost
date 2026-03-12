---
name: grok-hotposts-cli
description: 通过 Grok AI 搜集 X (Twitter) 热门帖子，支持自定义主题、时间范围和数量，输出 JSON。当用户说"搜集热门推文"、"X上的热点"、"Twitter趋势"、"AI资讯"、"科技动态"、"获取热帖"、"grok搜集"、"热门帖子"时使用。
---
# Grok Hot Posts CLI

## 用途
通过 Grok AI 搜集 X 平台上的热门帖子，返回结构化 JSON 数据。

## ⚠️ Agent 执行流程（必读）

当 Agent 使用此 skill 时，**必须按以下完整流程执行**：

1. **运行脚本**：根据用户需求构建命令并执行
2. **优先使用 `--json-only`**：直接从 stdout 获取最终 JSON
3. **只有在显式使用文件输出模式时**：再去读取 `hot_posts_output/*.json`
4. **将结果格式化呈现给用户**：以可读的表格/列表形式展示，包含以下信息：
   - 序号、作者、发帖时间
   - 中文摘要
   - 👁 浏览量 / ❤️ 点赞 / 🔁 转发
   - 帖子链接（可点击）

**❌ 禁止**：只告诉用户「文件已保存到 xxx.json」就结束
**✅ 必须**：直接读取 JSON 结果并呈现完整内容

示例呈现格式：
```
| # | 作者 | 时间 | 摘要 | 👁 浏览 | ❤️ 赞 | 🔁 转 | 链接 |
|---|------|------|------|---------|-------|-------|------|
| 1 | @openai | 2026-02-12 03:17 | GPT-4o 发布... | 2,000,000 | 50,000 | 12,000 | [链接](url) |
```

## 🤖 Agent 长时间命令执行指南（Cursor/OpenClaw 必读）

> ⚠️ **这是一个长时间运行命令（通常 3-5 分钟）**，不要因为短时间内没有 stdout 输出就认为脚本出错或卡死。

### 执行参数要求

使用 `run_command` 工具时，必须设置以下参数：

```
WaitMsBeforeAsync: 10000    # 至少等待 10 秒再转后台（脚本启动浏览器约需 5-8 秒）
```

使用 `command_status` 轮询时，必须设置：

```
WaitDurationSeconds: 300    # 等待最多 300 秒（5 分钟），让命令有充足时间完成
```

### stderr 进度输出

脚本在 `--json-only` 模式下，**stdout 只包含最终 JSON**，但 **stderr 会输出实时进度信息**，格式如下：

```
[11:05:30] 🌐 启动浏览器...
[11:05:38] ✅ 浏览器已启动
[11:05:39] 🔗 打开 Grok 页面...
[11:05:45] 🆕 新建 Grok 对话...
[11:05:48] 📝 输入提示词...
[11:05:52] ✅ 提示词已发送，等待 Grok 响应...
[11:05:55] ⏳ 等待 Grok 回复（超时: 300s）...
[11:06:25] ⏳ Grok 生成中... (30s / 300s)
[11:06:55] ⏳ Grok 生成中... (60s / 300s)
[11:08:10] ✅ Grok 回复完成 (135s, 4200 字符)
[11:08:10] 📋 解析 Grok 回复 (4200 字符)...
[11:08:10] 🏁 完成！获取 10 条帖子
[11:08:12] 🔒 关闭浏览器...
```

Agent 在调用 `command_status` 时可以看到这些 stderr 进度信息，据此判断脚本是否正在正常工作。

### ❌ 常见错误做法

1. **不要使用太短的 WaitDurationSeconds**（如 5 秒）然后反复轮询 — 浪费 Agent 回合且可能误判为超时
2. **不要因为 stdout 无输出就判断脚本卡死** — `--json-only` 模式下 stdout 只在最终才输出
3. **不要在脚本运行中途终止它** — Grok Thinking 搜索需要 1-3 分钟，属于正常等待

### ✅ 正确执行模板

```
步骤1: run_command（WaitMsBeforeAsync=10000）
  命令: cd /Users/jackwl/Code/gitcode/gitxPost && source .venv/bin/activate && python3 grok_hot_posts.py --json-only [其他参数]

步骤2: command_status（WaitDurationSeconds=300）
  等待命令完成，查看 stderr 进度和最终 stdout JSON 输出

步骤3: 如果 stdout 包含 JSON，直接解析并展示
       如果命令失败，检查 stderr 中的错误信息
```

## 前置条件
1. 进入项目目录并激活虚拟环境：
   ```bash
   cd /Users/jackwl/Code/gitcode/gitxPost
   source .venv/bin/activate
   ```
2. 需要已登录 X 的 Chrome 配置文件（首次需手动登录）
3. 需要 X Premium+ 订阅（Grok 访问权限）

## 命令格式

```bash
python3 grok_hot_posts.py [参数]
```

### 核心参数
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-n, --count` | 帖子数量 | 10 |
| `--hours` | 时间范围（小时） | 72 |
| `--topics` | 搜索主题（空格分隔多个） | AI 科技 开源Github |
| `--tags` | 内容标签，细化搜索（可选） | 无 |

### 输出参数
| 参数 | 说明 |
|------|------|
| `--json-only` | 仅输出 JSON 到 stdout（推荐 Agent 使用） |
| `--output DIR` | 输出目录（默认：./hot_posts_output） |
| `-q, --quiet` | 静默模式 |

### 高级参数
| 参数 | 说明 |
|------|------|
| `--timeout N` | Grok 回复超时秒数（默认：300，Grok Thinking 需要较长时间） |
| `--prompt TEXT` | 自定义提示词（覆盖 topics/count/hours） |

## 场景决策指南

根据用户意图选择合适的参数组合：

**用户想快速了解最新动态？**
```bash
python3 grok_hot_posts.py --hours 24 --count 10
```

**用户想搜集特定领域？**
```bash
python3 grok_hot_posts.py --topics "大模型" "机器学习" --count 15
```

**用户想细化搜索方向？**
```bash
python3 grok_hot_posts.py --topics "AI" --tags "突破" "融资" "开源"
```

**Agent/脚本集成？** → 必须加 `--json-only`（自动启用 quiet 模式，stdout 仅输出纯 JSON）
```bash
python3 grok_hot_posts.py --json-only --count 20 --hours 48
```

**用户要定时监控多主题？**
```bash
python3 grok_hot_posts.py --topics "AI" --output ./ai_trends --quiet
python3 grok_hot_posts.py --topics "区块链" --output ./crypto_trends --quiet
```

## 排序与截取规则

输出结果自动处理：
1. **按浏览量降序**排列（views 最高的在前）
2. 浏览量相同时，**按时间降序**（最新的在前）
3. 最终 JSON **只输出 top 10 条**（无论 Grok 返回多少条）

## JSON 输出格式

`--json-only` 模式输出：
```json
{
  "ok": true,
  "count": 10,
  "topics": ["AI", "科技", "开源Github"],
  "hours": 72,
  "posts": [
    {
      "time": "2026-02-12 03:17:18",
      "author": "@openai",
      "summary": "OpenAI 发布全新 GPT-4o 模型，支持语音通话。",
      "views": 2000000,
      "likes": 50000,
      "reposts": 12000,
      "url": "https://x.com/openai/status/12345678"
    }
  ]
}
```

文件模式输出到 `--output` 目录：
- `grok_raw_YYYYMMDD_HHMMSS.txt`：原始回复
- `hot_posts_YYYYMMDD_HHMMSS.json`：解析后的 JSON

## 退出状态码
| 状态码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 登录失败 |
| 2 | 发送提示词失败 |
| 3 | 未获取到回复 |
| 4 | 解析失败 |
| 5 | 其他错误 |
| 130 | 用户中断 |

## 注意事项
- 首次运行需手动在浏览器里登录 X（脚本等待 300 秒）
- 可通过环境变量 `XPOST_PROFILE_DIR` 指定 Chrome 配置文件路径
- 避免高频调用，以免触发 X 速率限制
