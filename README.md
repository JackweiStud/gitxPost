# gitxPost

`gitxPost` 是一套面向 macOS 的 X 自动化工具集，覆盖从 Markdown 创作、AI 配图、X Articles 长文发布、X Post 短帖发布，到用 Grok 搜集热点内容的完整工作流。

当前项目适合两类使用方式：

- 手工使用 CLI
- 作为 Agent / Skill / 自动化系统的本地执行后端

## 核心能力

项目当前已覆盖这些真实能力：

- `Article`
  - 从 Markdown 解析并发布到 X Articles
  - 支持草稿、真发布、封面图、内容图
- `Post`
  - 发布 280 字以内短帖
  - 支持草稿、真发布、最多 4 张图片
- `Grok Hot Posts`
  - 通过 Grok 搜集 X 热门帖子并输出结构化 JSON
- `Markdown Authoring`
  - 提供文章模板、示例、风格 Prompt
- `AI Auto Images`
  - 通过 Antigravity workflow 给文章自动配图
- `CLI + Skills`
  - 提供 `xpost` CLI
  - 提供面向 Agent 的 skill 定义
- `CI / 验收`
  - 提供统一测试用例和测试报告模板
- `Changelog`
  - 项目要求每次提交前更新 `CHANGELOG.md`

## 当前真实状态

截至 2026-03-12，已经实测通过：

- `Article` 草稿
- `Article` 真发布
- `Article` 内容图 / 封面图上传
- `Post` 纯文本
- `Post` 图文
- `Grok` JSON 输出

## 技术路线

当前三条自动化链路都已经统一到：

- 真实 Google Chrome profile
- Patchright CDP 附着
- 共享浏览器会话层：`browser_cdp_session.py`

对应入口：

- `Article`
  - CLI：`xpost publish`
  - 核心实现：`auto_publish_uc.py`
- `Post`
  - CLI：`xpost post` / `xpost post-login`
  - 核心实现：`auto_publish_post.py`
- `Grok`
  - CLI：`grok_hot_posts.py`
  - 核心实现：`grok_hot_posts.py`

## 快速开始

### 1. 安装

```bash
cd /Users/jackwl/Code/gitcode/gitxPost

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. 环境检查

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
xpost doctor
```

### 3. 首次登录

项目默认复用本地 Chrome profile：

- `chrome_data_mirror`：Article / Post / Grok 主 profile
- `patchright_post_data`：Post 相关历史持久化目录，保留为本地运行态

如果需要先初始化 Post 登录：

```bash
xpost post-login
```

## CLI 概览

```bash
xpost init ...
xpost validate ...
xpost parse ...
xpost publish ...
xpost post ...
xpost post-login ...
xpost doctor
```

所有子命令都输出 JSON，适合脚本和 Agent 调用。

## 典型工作流

### 1. 创作 Markdown 文章

生成文章骨架：

```bash
xpost init CreateMd/your_article.md --topic "你的主题" --style zara
```

校验格式：

```bash
xpost validate CreateMd/your_article.md
```

解析为 JSON：

```bash
xpost parse CreateMd/your_article.md
```

### 2. 使用多风格 Prompt 写文

内置 3 种写作风格：

| 风格 | 文件 | 场景 |
|------|------|------|
| `zara` | `CreateMd/prompts/prompt_zara.md` | 经验分享、产品洞察 |
| `tech` | `CreateMd/prompts/prompt_tech.md` | 技术教程、架构分析 |
| `fun` | `CreateMd/prompts/prompt_fun.md` | 轻松科普、幽默表达 |

### 3. 用 Antigravity 自动配图

工作流文件：

- `.agent/workflows/auto-imgByMdCn.md`

在 Antigravity 对话中执行：

```bash
/auto-imgByMdCn.md CreateMd/your_article.md
```

这个工作流会：

1. 读取 Markdown
2. 识别图片占位符
3. 分析上下文并构造 Prompt
4. 调用图片生成能力
5. 写回文章 `images/` 目录

### 4. 发布 Article

保存草稿：

```bash
xpost publish CreateMd/articleNew.md --no-wait
```

直接发布：

```bash
xpost publish CreateMd/articleNew.md --publish --no-wait
```

### 5. 发布 Post

纯文本：

```bash
xpost post "Hello world" --publish
```

图文：

```bash
xpost post "这是一条图文 Post" --images /path/to/image.png --publish
```

草稿：

```bash
xpost post "先存草稿" --no-wait
```

可观察模式：

```bash
xpost post "Visible flow" --images /path/to/image.png --publish --observe-ms 2500
```

### 6. 用 Grok 搜集热点

默认：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --json-only
```

自定义主题：

```bash
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py \
  --topics OpenClaw skills GitHub \
  --hours 168 \
  --count 5 \
  --json-only
```

## Skills 与 Agent 集成

项目内置两个可直接复用的 skill：

- `skills/xpost-cli/SKILL.md`
- `skills/grok-hotposts-cli/SKILL.md`

适用场景：

- Agent 调用 `xpost` CLI 发布文章
- Agent 调用 Grok CLI 搜集热点帖子

## 测试与验收

统一测试入口在 `CI/`：

- `CI/README.md`
- `CI/test-cases.md`
- `CI/report-template.md`

推荐最小回归集：

1. `TC-01` Article 草稿
2. `TC-03` Article 图片上传
3. `TC-04` Grok JSON 输出
4. `TC-06` Post 纯文本

## 目录结构

```text
gitxPost/
├── xpost.py
├── auto_publish_uc.py
├── auto_publish_post.py
├── grok_hot_posts.py
├── browser_cdp_session.py
├── requirements.txt
├── pyproject.toml
├── CHANGELOG.md
├── README.md
├── CI/
│   ├── README.md
│   ├── test-cases.md
│   └── report-template.md
├── docs/
│   ├── x-post-implementation-overview-2026-03-09.md
│   ├── post-lessons-learned-2026-03-09.md
│   ├── article-grok-cdp-migration-prd-2026-03-09.md
│   ├── article-grok-cdp-migration-test-cases-2026-03-09.md
│   ├── repo-structure-audit-2026-03-12.md
│   ├── supporting-capabilities-audit-2026-03-12.md
│   └── open-source-cleanup-checklist-2026-03-12.md
├── CreateMd/
│   ├── template.md
│   ├── articleNew.md
│   ├── agent_skill_guide.md
│   ├── prompts/
│   ├── images/
│   └── testmd/
├── skills/
│   ├── xpost-cli/
│   └── grok-hotposts-cli/
├── scripts/
│   └── install_cli.sh
├── .agent/
│   └── workflows/
│       └── auto-imgByMdCn.md
└── pasreMarkDown/
```

说明：

- `CreateMd/` 当前是文章内容工作区，适合放 Markdown、图片、Prompt、示例
- `pasreMarkDown/` 是历史保留目录，名字里有 typo，短期先保留，后续再考虑重构
- `chrome_data_mirror/` 和 `patchright_post_data/` 属于本地运行态，不建议提交到 Git

## 当前还缺什么

如果目标是“GitHub 开源后，别人拉下来就能理解、能用、能继续维护”，当前还建议补这几类内容：

- 更统一的目录命名
  - `CreateMd/`、`pasreMarkDown/` 都偏历史命名，不够直观
- 更清晰的示例分层
  - 正式示例和历史测试样例目前仍有混放
- 更明确的配置入口
  - `config.py` 不是当前唯一配置源，后续需要收敛
- 更自动化的验收
  - 现在已有 `CI/` 文档，但还不是完全自动执行的 CI pipeline
- 更清晰的对外边界
  - 当前最佳运行环境是 macOS + 已登录的本地 Chrome profile，这一点已经应当在开源说明里持续强调

推荐路线：

1. 先保持代码结构稳定，以 README + docs + CI 文档为主完成开源整理
2. 后续再做目录重命名和更彻底的模块化重构

更详细的结构建议见：

- `docs/repo-structure-audit-2026-03-12.md`

## Changelog 规则

项目要求：

- 每次准备 `git commit` 前，先更新 `CHANGELOG.md`
- 如果改动影响测试或交付信心，顺手更新 `CI/` 文档

相关规则文件：

- `.cursor/rules/changelog-before-commit.mdc`
