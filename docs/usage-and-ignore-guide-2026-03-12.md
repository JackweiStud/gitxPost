# gitxPost 使用与忽略规则指南

日期：2026-03-12

这份文档主要回答两个问题：

1. 这个项目现在应该怎么用
2. 哪些目录和文件只应该保留在本机，不应该提交进 git

## 1. 环境准备

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

建议先执行一次：

```bash
xpost doctor
```

## 2. 主功能入口

### 2.1 Article 长文

保存草稿：

```bash
xpost publish /Users/jackwl/Code/gitcode/gitxPost/content/examples/articleNew.md --no-wait
```

真实发布：

```bash
xpost publish /Users/jackwl/Code/gitcode/gitxPost/content/examples/articleNew.md --publish --no-wait
```

### 2.2 Post 短帖

纯文本：

```bash
xpost post "hello world" --publish
```

图文：

```bash
xpost post "image post" --images /absolute/path/to/image.png --publish
```

如果需要初始化 Post 登录态：

```bash
xpost post-login
```

### 2.3 Grok 热点搜索

```bash
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --topics "OpenClaw skills GitHub" --hours 168 --count 5 --json-only
```

### 2.4 X 雷达

扫描：

```bash
xpost radar-scan
```

分析：

```bash
xpost radar-analyze --days 7
```

账号管理：

```bash
xpost radar-accounts list
xpost radar-accounts add NewAccount "推荐原因"
xpost radar-accounts remove NewAccount
xpost radar-accounts restore NewAccount
```

## 3. Markdown 创作工作流

初始化文章骨架：

```bash
xpost init content/drafts/your_article.md --topic "你的主题" --style tech
```

重要说明：

- `xpost init` 只生成文章骨架，不会直接生成完整正文
- `--style` 会把对应 Prompt 写进 Markdown 顶部注释
- 真正的正文可以通过 `xpost generate` 直接生成，也可以再交给 Claude / OpenClaw / Codex 等外部 LLM 生成，并覆盖模板占位内容

推荐最小闭环：

1. `xpost init ...`
2. `xpost generate ...`
3. 用 Antigravity 自动配图
4. `xpost validate ...`
5. `xpost publish ... --no-wait`
6. 确认后再 `xpost publish ... --publish --no-wait`

生成正文：

```bash
xpost generate content/drafts/your_article.md
```

说明：

- 默认优先读取 `XPOST_LLM_API_KEY` / `XPOST_LLM_API_URL` / `XPOST_LLM_MODEL`
- 如果本机存在 `~/.openclaw/scripts/tokenmax.sh`，会自动把其中的 TokenMax 配置作为回退
- 原骨架会自动备份为 `*.skeleton.<timestamp>.md`

校验与解析：

```bash
xpost validate content/drafts/your_article.md
xpost parse content/drafts/your_article.md
```

补充说明：

- `validate` 只检查结构
- `parse` 只输出结构化 JSON
- 这两步不会帮你写正文

Antigravity 自动配图：

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

说明：
- 自动配图依赖 Antigravity 外部运行环境
- 仓库中保留的是 workflow 入口，不是独立可执行脚本

团队协作时，建议直接参考：

- `docs/article-minimal-loop-runbook-2026-03-13.md`

## 4. 当前目录职责

需要长期保留并纳入版本控制：

- `content/`
- `article_tooling/scripts/`
- `skills/`
- `xinfo/`
- `docs/`
- `CI/`
- `xpost.py`
- `auto_publish_uc.py`
- `auto_publish_post.py`
- `grok_hot_posts.py`
- `browser_cdp_session.py`

本地运行态，保留在本机但不要提交：

- `chrome_data_mirror/`
- `patchright_post_data/`
- `.venv/`
- `content/drafts/` 下你自己的草稿
- `CI/reports/`
- `hot_posts_output/`

原因：
- 这些目录包含登录态、浏览器用户数据、运行缓存或个人测试产物
- 提交进 git 既不安全，也会污染仓库

## 5. 默认忽略规则

这些类型的文件应始终忽略：

- `*.log`
- `*.backup`
- `__pycache__/`
- `.cache/`
- `.playwright-cli/`
- `debug_output/`

这些规则已经体现在 `.gitignore` 中。

## 6. 提交前检查顺序

每次准备提交前，建议按这个顺序处理：

1. 更新 `CHANGELOG.md`
2. 如果功能或验收结论变化，同步更新 `CI/`
3. 检查 `git status`
4. 确认没有把本地运行态、日志、缓存、截图误提交

建议至少执行一轮最小回归：

1. `TC-01` Article 草稿
2. `TC-03` Article 图片上传
3. `TC-04` Grok JSON 输出
4. `TC-06` Post 纯文本

## 7. 新功能如何补文档

新增功能后，至少补这三处：

1. `README.md`
2. `CI/test-cases.md`
3. `CHANGELOG.md`

如果是高频使用能力，建议额外补：

- `docs/` 下的专题说明
- 对应 `skills/` 的使用说明

## 8. 推荐理解方式

可以把这个项目理解成三层：

1. 业务层：`Article`、`Post`、`Grok`
2. 工作流层：Markdown 模板、Prompt、Antigravity workflow、skills
3. 运维与验收层：`xpost doctor`、`CI/`、`CHANGELOG.md`、`.gitignore`

这样比较容易判断某个文件到底属于：
- 主流程源码
- 文档与示例
- 还是只应保留在本地的运行态数据
