---
name: x-reply-assistV2
description: >-
  自动回复指定 X/Twitter 推文：提取原帖正文、AI 生成 3 条回复备选、用户选择后逐字模拟人类打字填入并发送。
  通过 xpost CLI + patchright CDP 直连本地 Chrome 执行，不依赖 browser MCP。
  当用户提到「回复推文」「reply 这条」「给这个帖子回复」「回一下」「帮我回」「reply this tweet」
  或给出 x.com/*/status/* URL 并要求回复时使用。
---

# x-reply-assistV2

## 前置条件

1. Chrome 已通过 `xpost post-login` 完成登录态持久化
2. `/Users/jackwl/Code/gitcode/gitxPost/.env` 已配置 `XPOST_LLM_API_KEY`、`XPOST_LLM_API_URL`、`XPOST_LLM_MODEL`
3. gitxPost venv 已安装 `patchright`、`httpx`、`python-dotenv`

如果前置条件不满足，提示用户修复后再执行，不要尝试跳过。

## Shell 环境

所有命令均在以下环境执行，后续步骤不再重复写：

```bash
cd /Users/jackwl/Code/gitcode/gitxPost && source .venv/bin/activate
```

## 执行流程

严格按顺序执行，不可跳过、合并或重排步骤。

### Step 1 — 提取推文正文

```bash
python xpost.py reply-extract "<tweet_url>"
```

- `<tweet_url>` 直接使用用户给出的原始 URL，CLI 内部会自动清理锚点和查询参数
- 预期耗时：10-20 秒（含浏览器启动和页面加载）
- 返回 JSON，检查 `ok` 字段

成功示例：
```json
{"ok": true, "handle": "Alice\n@alice_dev", "text": "推文正文...", "lang": "en"}
```

**如果 `ok: false`** → 向用户报告错误信息，终止流程。

### Step 2 — 生成 3 条回复备选

```bash
python /Users/jackwl/.openclaw/agents/xagent/workspace/skills/x-reply-assistV2/scripts/generate_replies.py "<tweet_text>" "<handle>"
```

- `<tweet_text>` 和 `<handle>` 取自 Step 1 返回的 `text` 和 `handle` 字段
- 如果文本包含双引号，用单引号包裹参数；如果同时包含单双引号，用 `$'...'` 语法转义
- 预期耗时：5-15 秒

返回 JSON：
```json
{"A": "追问型回复", "B": "实践型回复", "C": "简短点赞型回复"}
```

**如果返回 `error` 字段** → 向用户报告错误，终止流程。

### Step 3 — 展示备选，等用户选择

向用户展示，格式固定如下：

```
回复备选：
A（追问）：<A 内容>
B（实践）：<B 内容>
C（简短）：<C 内容>

请选 A / B / C，或直接输入自定义内容。
```

**必须等待用户回复，不可自行选择或跳过。**

### Step 4 — 发送回复（需二次确认）

用户选择后，先展示最终内容并请求确认：

```
即将回复 @<handle>：
「<最终回复内容>」

确认发送？回复「发送」继续，「取消」放弃。
```

**必须等用户明确说「发送」「确认」「Y」「是」才继续。任何其他回复视为取消。**

### Step 5 — 执行发送

```bash
python xpost.py reply "<tweet_url>" "<reply_text>" --publish --observe-ms 900
```

- `<tweet_url>` 使用用户给出的原始 URL
- `<reply_text>` 使用用户确认的最终文本
- 引号转义规则同 Step 2
- 预期耗时：35-50 秒（含页面预热、逐字打字、发送确认）
- 返回 JSON，检查 `ok` 字段

**如果 `ok: false`** → 向用户报告错误，不自动重试。

### Step 6 — 记录日志

发送成功后，写入 `memory/YYYY-MM-DD.md`：

```
- [HH:MM] reply-assist 发送成功：回复 @<handle> / <内容前30字>...
```

## 错误处理

| 情况 | 处理 |
|------|------|
| reply-extract 返回 `ok: false` | 报告用户，终止 |
| generate_replies 返回 `error` | 报告用户，终止 |
| reply --publish 返回 `ok: false` | 报告用户，**不自动重试发送** |
| 命令超过 60 秒无输出 | 可能浏览器卡住，报告用户 |
| 登录态失效（错误信息含 "post-login"） | 提示用户运行 `xpost post-login` |

## 禁止行为

- **禁止** 跳过 Step 4 的人工确认直接发送
- **禁止** 自动重试失败的发送操作
- **禁止** 批量处理多条 URL（单次只处理一条）
- **禁止** 在用户未确认时执行 `--publish`
- **禁止** 自行编造或修改用户选择的回复内容
- **禁止** 使用 browser MCP 工具替代 xpost CLI 命令

## 文件结构

```
skills/x-reply-assistV2/
├── SKILL.md                    # 本文件
└── scripts/
    └── generate_replies.py     # LLM 生成 3 条备选（httpx）
```

底层模块位于 `/Users/jackwl/Code/gitcode/gitxPost/`：`xpost.py`（CLI 入口）、`auto_reply_post.py`（Reply 核心）、`browser_cdp_session.py`（浏览器会话）。
