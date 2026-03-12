# gitxPost 统一测试用例

日期基线：2026-03-12
适用范围：`Article` / `Grok` / `Post`

## 1. 测试目标

这套用例用于验证：

1. 功能改动后核心业务仍可用
2. 共享浏览器会话层改动不会误伤现有链路
3. Chrome 升级后不再因 driver 匹配问题导致核心功能失效

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

### TC-01 Article 草稿

目标：
- 验证 `Article` 仍可复用登录态并完成草稿链路

执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/CreateMd/articleNew.md --no-wait
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
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/CreateMd/articleNew.md --publish --no-wait
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
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/CreateMd/agent_skill_guide.md --no-wait
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
  --images /Users/jackwl/Code/gitcode/gitxPost/CreateMd/images/demo1.png \
  --no-wait
```

预期：
- 文本成功输入
- 图片成功上传
- 返回 JSON：`ok=true`

## 5. 增量补充规则

以后新增功能时，测试用例按下面规则补：

1. 新增一个功能，至少补一个成功用例
2. 新增一个高风险边界，至少补一个失败用例
3. 影响共享浏览器会话层时，必须补“旧功能不被误伤”的回归用例
4. 涉及真实外发时，必须区分“草稿验证”和“真实发布验证”
