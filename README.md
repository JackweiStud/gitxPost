# gitxPost

`gitxPost` 是一套面向 macOS 的 X 自动化工具集，覆盖：

- Markdown 创作与模板
- 多风格 Prompt
- Antigravity 自动配图工作流
- X Articles 长文发布
- X Post 短帖发布
- Grok 热点搜索
- CLI 与 Agent skills 集成
- 测试验收与 changelog 约束

当前项目适合两类使用方式：

- 手工使用 CLI
- 作为 Agent / Skill / 自动化系统的本地执行后端

## 当前真实状态

截至 2026-03-12，已经实测通过：

- `Article` 草稿
- `Article` 真发布
- `Article` 内容图 / 封面图上传
- `Post` 纯文本
- `Post` 图文
- `Grok` JSON 输出
- `xpost init -> validate -> parse`

## 技术路线

当前三条自动化链路统一到：

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

### 3. 登录态

项目默认复用本地 Chrome profile：

- `chrome_data_mirror`
- `patchright_post_data`

如果需要初始化 Post 登录：

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

更完整的使用与忽略规则见：

- `docs/usage-and-ignore-guide-2026-03-12.md`

## 典型工作流

### 1. 创建文章骨架

```bash
xpost init content/drafts/your_article.md --topic "你的主题" --style zara
```

说明：

- 会自动创建 `content/drafts/images/`
- 会自动复制示例 `cover.png` 和 `demo1.png`

### 2. 校验与解析 Markdown

```bash
xpost validate content/drafts/your_article.md
xpost parse content/drafts/your_article.md
```

### 3. 使用多风格 Prompt 写文

内置 3 种写作风格：

| 风格 | 文件 | 场景 |
|------|------|------|
| `zara` | `content/prompts/prompt_zara.md` | 经验分享、产品洞察 |
| `tech` | `content/prompts/prompt_tech.md` | 技术教程、架构分析 |
| `fun` | `content/prompts/prompt_fun.md` | 轻松科普、幽默表达 |

Prompt 使用说明见：

- `content/prompt-guide.md`

### 4. 用 Antigravity 自动配图

工作流文件：

- `.agent/workflows/auto-imgByMdCn.md`

在 Antigravity 对话中执行：

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

说明：

- 这是 Antigravity 集成能力
- 依赖 Antigravity 自身的 workflow 运行环境
- 不属于本仓库内可完全独立自测的脚本能力

### 5. 发布 Article

保存草稿：

```bash
xpost publish content/examples/articleNew.md --no-wait
```

直接发布：

```bash
xpost publish content/examples/articleNew.md --publish --no-wait
```

### 6. 发布 Post

纯文本：

```bash
xpost post "Hello world" --publish
```

图文：

```bash
xpost post "This is an image post" --images /path/to/image.png --publish
```

### 7. 用 Grok 搜集热点

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --json-only
```

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
├── docs/
├── skills/
│   ├── README.md
│   ├── xpost-cli/
│   └── grok-hotposts-cli/
├── content/
│   ├── template.md
│   ├── prompt-guide.md
│   ├── prompts/
│   ├── examples/
│   │   ├── articleNew.md
│   │   ├── agent_skill_guide.md
│   │   ├── images/
│   └── drafts/
├── article_tooling/
│   └── scripts/
├── scripts/
│   └── install_cli.sh
└── .agent/workflows/
```

## Skills 关系

当前 repo 级 skills 只保留两类“正在使用的入口”：

- `skills/xpost-cli/SKILL.md`
  - 统一处理 Article / Post 的 CLI 工作流
- `skills/grok-hotposts-cli/SKILL.md`
  - 处理 Grok 热点搜索

历史上独立存在的 `x-article-publisher` skill 已经不再作为 repo 主入口。  
它的可复用脚本保留在 `article_tooling/scripts/`，历史说明统一收敛到文档。

更详细的拆分与合并关系见：

- `docs/skill-topology-2026-03-12.md`
- `skills/README.md`

## 测试与验收

统一入口在：

- `CI/README.md`
- `CI/test-cases.md`
- `CI/report-template.md`

最近一次真实 smoke 结果样例已经记录在：

- `CI/report-template.md`

推荐最小回归集：

1. `TC-01` Article 草稿
2. `TC-03` Article 图片上传
3. `TC-04` Grok JSON 输出
4. `TC-06` Post 纯文本

## 开源第二轮整理结论

这一轮已经完成的整理：

- `CreateMd/` 重构为 `content/`
- `pasreMarkDown/` 重构为 `article_tooling/`
- 运行时代码切到新目录
- `config.py` 清理出仓库
- `pyEnv.py`、旧 article skill/plugin 文档与元数据清理出仓库
- repo 级 skills 与历史 skill 完成角色分离

## 本地运行态与忽略规则

下面这些目录默认只保留在本机，不应提交进 git：

- `chrome_data_mirror/`
- `patchright_post_data/`
- `.venv/`
- `content/drafts/` 中你自己的草稿
- `CI/reports/`
- `hot_posts_output/`

日志、缓存和调试产物同样应忽略，例如：

- `*.log`
- `*.backup`
- `__pycache__/`
- `debug_output/`

完整说明见：

- `.gitignore`
- `docs/usage-and-ignore-guide-2026-03-12.md`

当前仍建议后续继续做的事：

- 进一步优化示例文件命名
- 评估是否把 `docs/` 继续拆成 `guides/`、`audits/`、`history/`
- 逐步把仓库整理成更标准的模块化包结构

## 相关文档

- `docs/repo-structure-audit-2026-03-12.md`
- `docs/supporting-capabilities-audit-2026-03-12.md`
- `docs/open-source-cleanup-checklist-2026-03-12.md`
- `docs/skill-topology-2026-03-12.md`
- `docs/usage-and-ignore-guide-2026-03-12.md`

## Changelog 规则

项目要求：

- 每次准备 `git commit` 前，先更新 `CHANGELOG.md`
- 如果改动影响测试或交付信心，顺手更新 `CI/` 文档

规则文件：

- `.cursor/rules/changelog-before-commit.mdc`
