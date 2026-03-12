# gitxPost 迁移 Change Log

日期：2026-03-12

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
