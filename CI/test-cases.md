# gitxPost 统一测试用例

日期基线：2026-03-12
适用范围：`Article` / `Grok` / `Post` / `Radar`

## 1. 测试目标

这套用例用于验证：

1. 功能改动后核心业务仍可用
2. 共享浏览器会话层改动不会误伤现有链路
3. Chrome 升级后不再因 driver 匹配问题导致核心功能失效
4. Markdown 起稿到成文的生成闭环可用
5. X 雷达扫描与分析入口可用
6. X 雷达日报与周报生成链路可用

## 2. 测试前提

- macOS
- 已安装 Google Chrome
- 已准备 `.venv`
- 当前账号已具备 X 登录态
- `Article` 测试素材可用
- 测试账号具备 Grok 可用权限

建议先执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py doctor
```

## 3. 验收原则

不要只看“脚本没报错”，而要看：

- 是否真正进入目标页面
- 是否复用登录态
- 是否真正完成业务动作
- 输出内容是否符合预期

## 4. 测试用例

### TC-00 Article 成文生成

目标：
- 验证 `xpost generate` 能把文章骨架扩写成真实 Markdown 成文

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py init /tmp/gitxpost_tc00.md --topic "OpenClaw ACP 避坑指南" --style zara --force
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py generate /private/tmp/gitxpost_tc00.md --model claude-sonnet-4-6
```

预期：
- 返回 JSON：`ok=true`
- 生成结果通过 `validate`
- 结果中不再保留模板占位句子

### TC-01 Article 草稿

目标：
- 验证 `Article` 仍可复用登录态并完成草稿链路

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/content/examples/articleNew.md --no-wait
```

预期：
- 不进入登录页
- 能进入 Article 编辑器
- 标题、正文、封面图进入编辑器
- 返回 JSON：`ok=true`，`mode=draft`

### TC-02 Article 真发布

目标：
- 验证 `Article` 正式发布路径可用

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/content/examples/articleNew.md --publish --no-wait
```

预期：
- 不进入登录页
- 发布按钮可达
- 页面出现发布完成迹象
- 返回 JSON：`ok=true`，`mode=publish`

注意：
- 这是外发动作，执行前要明确确认

### TC-03 Article 图片上传

目标：
- 验证内容图与封面图链路可用

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/content/examples/agent_skill_guide.md --no-wait
```

预期：
- 内容图上传成功
- 封面图上传成功
- 封面 `Apply` 成功
- 返回 JSON：`ok=true`

### TC-04 Grok JSON 输出

目标：
- 验证 Grok 能返回结构化 JSON

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --topics AI 科技 --hours 24 --count 5 --json-only
```

预期：
- 不进入登录页
- 能打开 Grok
- stdout 返回可解析 JSON
- 每条记录包含 `time author summary views likes reposts url`

### TC-05 Chrome 升级风险回归

目标：
- 验证改动后不再依赖 `chromedriver` 版本精确匹配

执行：
- 升级本机 Chrome 后，不修改任何 `version_main`
- 重新执行 `TC-01` 和 `TC-04`

预期：
- 两条链路都仍可运行
- 不需要手改版本号

### TC-06 Post 纯文本

目标：
- 验证 Post 纯文本链路没有被误伤

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py post "smoke test after change" --no-wait
```

预期：
- 不进入登录页
- 文本成功输入
- 返回 JSON：`ok=true`

### TC-07 Post 图文

目标：
- 验证 Post 图文链路没有被误伤

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py post "smoke image test" \
  --images /Users/jackwl/Code/gitcode/gitxPost/content/examples/images/demo1.png \
  --no-wait
```

预期：
- 文本成功输入
- 图片成功上传
- 返回 JSON：`ok=true`

### TC-08 Radar 扫描

目标：
- 验证迁入 repo 的 X 雷达扫描入口可用

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py radar-scan
```

预期：
- 返回 JSON：`ok=true`
- `xinfo/RESULT.json` 被写入
- 输出中包含 `successful_accounts`、`failed_accounts`、`new_items_count`

### TC-09 Radar 分析

目标：
- 验证 X 雷达分析入口可用并输出结构化 JSON

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py radar-analyze --days 7
```

预期：
- 返回 JSON：`ok=true`
- 结果中包含 `network`、`account_stats`、`hot_topics`、`top_posts`

### TC-10 Radar 日报生成

目标：
- 验证 `radar-daily` 能基于扫描结果生成日报 Markdown，并更新行动追踪

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py radar-daily
```

预期：
- 返回 JSON：`ok=true`
- 生成 `xinfo/log/day/YYYY-MM-DD.md`
- 返回中包含 `actions_added`
- 默认模型为 TokenMax Opus 路径

### TC-11 Radar 周报生成

目标：
- 验证 `radar-weekly` 能基于分析结果生成周报 Markdown，并更新行动追踪

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py radar-weekly
```

预期：
- 返回 JSON：`ok=true`
- 生成 `xinfo/log/week/YYYY-MM-DD.md`
- 返回中包含 `actions_added`
- 默认模型为 TokenMax Opus 路径

## 5. 增量补充规则

以后新增功能时，测试用例按下面规则补：

1. 新增一个功能，至少补一个成功用例
2. 新增一个高风险边界，至少补一个失败用例
3. 影响共享浏览器会话层时，必须补“旧功能不被误伤”的回归用例
4. 涉及真实外发时，必须区分“草稿验证”和“真实发布验证”
