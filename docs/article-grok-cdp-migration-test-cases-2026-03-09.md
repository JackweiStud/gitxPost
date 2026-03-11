# 测试用例：Article 与 Grok 迁移验收

**项目**: `gitxPost`  
**日期**: 2026-03-09  
**用途**: 验证 `Article` 与 `Grok 热点搜索` 从 `undetected-chromedriver` 迁移到“真实 Chrome profile + Patchright CDP”后，功能没有丢失、没有被破坏

## 1. 测试目标

这份测试用例不是为了验证某个局部函数，而是为了验证迁移后两个老功能的核心业务结果仍然成立：

1. `Article` 还能正常进入编辑器并完成草稿/发布流程
2. `Grok 热点搜索` 还能正常得到结构化 JSON 结果
3. 两条链路都能复用同一个真实 Chrome 登录态
4. 两条链路都不再依赖 `chromedriver` 主版本匹配
5. 已经跑通的 `Post` 基础能力不能被迁移过程误伤

## 2. 测试范围

本次迁移验收覆盖：

- `Article` 草稿链路
- `Article` 直接发布链路
- `Grok 热点搜索 JSON 输出链路`
- 共享登录态复用链路
- `Post` 纯文本发布基础链路
- `Post` 图文发布基础链路

本次不覆盖：

- X 平台自身入口变化导致的产品级异常
- 没有 Grok 权限的账号
- 多账号并发占用同一 profile

## 3. 测试前提

执行测试前，必须满足：

- macOS
- 已安装 Google Chrome
- 已准备 `.venv`
- `patchright` 已安装
- 已存在可用的真实 Chrome 登录态
- `Article` 测试素材存在：`CreateMd/articleNew.md`
- 测试账号具备 Grok 可用权限

建议先执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py doctor
```

## 4. 验收原则

迁移是否通过，不看“脚本有没有报错”，而看下面这些真实结果：

- 页面能否真正进入目标功能区
- 登录态是否被复用
- 业务动作是否真正完成
- 最终输出是否符合预期

## 5. 测试用例

### TC-01：Article 草稿功能迁移后无回归

**目标**  
验证迁移后，`Article` 仍可复用真实 Chrome 登录态，并完成草稿链路。

**输入**  
Markdown 文件：

- `CreateMd/articleNew.md`

**步骤**

1. 激活虚拟环境
2. 执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/CreateMd/articleNew.md --no-wait
```

3. 观察浏览器是否：
   - 进入 Article 编辑器
   - 自动识别已登录状态
   - 输入标题
   - 粘贴正文
   - 上传封面图
4. 检查命令输出 JSON

**预期结果**

- 不出现再次登录 X 的要求
- 不出现 Chrome 版本不匹配错误
- 不出现 driver 下载错误
- 标题、正文、封面图都进入编辑器
- 返回 JSON 中 `ok = true`
- `mode = draft`

**失败判定**

出现以下任意一种即判失败：

- 进入登录页
- 编辑器未打开
- 标题/正文/图片未进入页面
- 返回 `ok = false`

### TC-02：Article 直接发布功能迁移后无回归

**目标**  
验证迁移后，`Article` 的正式发布能力没有丢失。

**输入**  
Markdown 文件：

- `CreateMd/articleNew.md`

**步骤**

1. 激活虚拟环境
2. 执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py publish /Users/jackwl/Code/gitcode/gitxPost/CreateMd/articleNew.md --publish --no-wait
```

3. 观察浏览器是否完成：
   - 标题输入
   - 正文输入
   - 封面图上传
   - 发布动作
4. 检查 X 侧是否出现发布成功后的页面状态变化

**预期结果**

- 不进入登录流程
- 不依赖 `version_main`
- 发布动作执行成功
- 返回 JSON 中 `ok = true`
- `mode = publish`

**失败判定**

- 进入登录页
- 发布按钮不可达
- 命令返回失败
- 页面没有任何发布完成迹象

### TC-03：Grok 热点搜索迁移后 JSON 输出无回归

**目标**  
验证迁移后，`Grok 热点搜索` 仍可输出结构化 JSON。

**输入**

- `topics = AI 科技`
- `hours = 24`
- `count = 5`

**步骤**

1. 激活虚拟环境
2. 执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --topics AI 科技 --hours 24 --count 5 --json-only
```

3. 观察浏览器是否：
   - 打开 Grok 页面
   - 复用已登录会话
   - 新建对话
   - 输入 prompt
   - 等待并完成 Grok 返回
4. 检查 stdout 输出内容

**预期结果**

- 不进入登录页
- 不出现 driver 下载和版本错误
- stdout 返回可解析 JSON
- JSON 为数组
- 数组长度大于等于 1
- 每条记录至少包含：
  - `time`
  - `author`
  - `summary`
  - `views`
  - `likes`
  - `reposts`
  - `url`

**失败判定**

- 返回非 JSON
- 返回空结果且无合理说明
- 进入登录页
- 无法进入 Grok 页面

### TC-04：共享登录态复用无回归

**目标**  
验证迁移后，`Article` 与 `Grok` 能共享同一个真实 Chrome 登录态，不需要分别重新登录。

**步骤**

1. 先执行一次 `Article` 草稿链路
2. 再执行一次 `Grok` JSON 输出链路
3. 全程不重新手工登录

**预期结果**

- 两条链路都直接进入业务页面
- 两条链路都复用同一个 profile
- 没有单独弹出新的登录初始化流程

**失败判定**

- 其中任一链路要求重新登录
- 其中任一链路掉回登录页

### TC-05：Chrome 升级后无需手改版本号

**目标**  
验证迁移后，系统 Chrome 主版本变化时，两条链路不再依赖人工修改 `version_main`。

**步骤**

1. 升级或确认当前系统 Chrome 已升级到新版本
2. 不修改任何 `version_main`
3. 重新执行：
   - TC-01
   - TC-03

**预期结果**

- 两条链路仍能正常运行
- 不需要修改源码中的 Chrome 主版本号
- 不出现 driver 版本不匹配错误

**失败判定**

- 需要人工修改 `version_main`
- 启动失败
- 出现 driver 版本错误

### TC-06：Post 纯文本发布无回归

**目标**  
验证迁移 `Article` / `Grok` 后，已跑通的 `Post` 纯文本发布能力没有被误伤。

**输入**

- 一条 280 字符以内的测试文本

**步骤**

1. 激活虚拟环境
2. 执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py post "迁移回归测试：纯文本 Post" --publish --no-wait
```

3. 观察浏览器是否：
   - 复用已登录 profile
   - 打开 Post 编辑器
   - 成功输入文本
   - 激活并点击发布按钮
4. 检查命令输出 JSON

**预期结果**

- 不出现登录初始化要求
- 文本成功进入编辑器
- 发布按钮可点击并执行
- 返回 JSON 中 `ok = true`
- `mode = publish`
- `images_count = 0`

**失败判定**

- 掉回登录页
- 文本输入失败
- 发布按钮不可点击
- 返回 `ok = false`

### TC-07：Post 图文发布无回归

**目标**  
验证迁移 `Article` / `Grok` 后，已跑通的 `Post` 图文发布能力没有被误伤。

**输入**

- 一条 280 字符以内的测试文本
- 1 张有效图片

**步骤**

1. 激活虚拟环境
2. 执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/xpost.py post "迁移回归测试：图文 Post" --images /path/to/image.png --publish --no-wait
```

3. 观察浏览器是否：
   - 打开 Post 编辑器
   - 输入文本
   - 上传图片
   - 成功点击发布按钮
4. 检查命令输出 JSON

**预期结果**

- 不进入登录流程
- 文本输入成功
- 图片被 X 识别并进入附件/预览区域
- 返回 JSON 中 `ok = true`
- `mode = publish`
- `images_count = 1`

**失败判定**

- 图片上传失败
- 发布按钮未激活
- 返回失败 JSON

## 6. 通过标准

本迁移只有在以下条件同时满足时，才可以判定通过：

1. TC-01 通过
2. TC-02 通过
3. TC-03 通过
4. TC-04 通过
5. TC-05 通过
6. TC-06 通过
7. TC-07 通过

如果其中任意一条失败，迁移都不能算完成。

## 7. 建议执行顺序

建议按这个顺序执行：

1. TC-01
2. TC-03
3. TC-04
4. TC-06
5. TC-07
6. TC-02
7. TC-05

原因：

- 先验证草稿与搜索，风险较低
- 再验证共享登录态和 `Post` 基础能力是否被误伤
- 最后验证正式发布和 Chrome 升级场景

## 8. 回归结论模板

测试完成后，建议按下面格式记录：

```text
迁移版本：
测试日期：
测试环境：
Chrome 版本：
Profile 路径：

TC-01：
TC-02：
TC-03：
TC-04：
TC-05：
TC-06：
TC-07：

总体结论：
是否允许合并：
```

## 9. 一句话结论

这份测试用例的核心目的不是“证明代码改了”，而是证明：

**迁移完成后，Article 和 Grok 的真实业务能力仍然存在，而且不再被 Chrome 升级轻易打断。**
