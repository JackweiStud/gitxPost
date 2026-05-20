# gitxPost

`gitxPost` 是一套面向 macOS 的 X 自动化工具集，覆盖：

- Markdown 创作与模板
- 多风格 Prompt
- Gemini Flash Image 自动配图工作流
- X Articles 长文发布
- LLM 生成真实文章正文
- X Post 短帖发布
- Grok 热点搜索
- X 雷达扫描 / 网络分析 / 账号管理
- X 雷达日报 / 周报生成
- CLI 与 Agent skills 集成
- 测试验收与 changelog 约束

当前项目适合两类使用方式：

- 手工使用 CLI
- 作为 Agent / Skill / 自动化系统的本地执行后端

## 文章存储结构

文章现在统一存放在 `xinfo/log/articles/<article_id>/` 下，每篇文章独立一个目录，典型结构是：

- `article.json`：文章元数据
- `article.md`：文章正文
- `images/`：该文章的配图文件

旧的平铺文件会在服务启动时自动迁移到新结构里。

## 当前真实状态

截至 2026-03-12，已经实测通过：

- `Article` 草稿
- `Article` LLM 成文生成
- `Article` 真发布
- `Article` 内容图 / 封面图上传
- `Post` 纯文本
- `Post` 图文
- `Grok` JSON 输出
- `xpost init -> validate -> parse`
- `Radar` 日报生成
- `Radar` 周报生成

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

### 1.1 配置 `.env`

项目现在支持从仓库根目录自动读取 `.env`，适合放本地 LLM API 配置。

推荐先复制：

```bash
cp /Users/jackwl/Code/gitcode/gitxPost/.env.example /Users/jackwl/Code/gitcode/gitxPost/.env
```

然后编辑 `.env`：

```dotenv
XPOST_LLM_API_KEY=your_tokenmax_api_key
XPOST_LLM_API_URL=https://tokenmax.vip/v1/messages
XPOST_LLM_MODEL=claude-sonnet-4-6
XPOST_RADAR_LLM_MODEL=claude-opus-4-6
XPOST_IMAGE_API_URL=http://127.0.0.1:8045/v1
XPOST_IMAGE_API_KEY=sk-your-key
XPOST_IMAGE_MODEL=gemini-3.1-flash-image
```

说明：

- `xpost generate` 默认读取 `XPOST_LLM_*`
- `xpost auto-img` 默认读取 `XPOST_IMAGE_*`；未单独配置时会回退到 `XPOST_LLM_FALLBACK_*`
- `xpost radar-daily` / `xpost radar-weekly` 默认读取 `XPOST_RADAR_LLM_MODEL`，未设置时回退到 `XPOST_LLM_MODEL`
- 若你已经手动 `export` 了同名环境变量，显式环境变量优先生效
- `.env` 已加入 `.gitignore`，不会进入仓库

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
xpost generate ...
xpost validate ...
xpost parse ...
xpost publish ...
xpost post ...
xpost post-login ...
xpost radar-scan ...
xpost radar-analyze ...
xpost radar-daily ...
xpost radar-weekly ...
xpost radar-accounts ...
xpost doctor
```

所有子命令都输出 JSON，适合脚本和 Agent 调用。

更完整的使用与忽略规则见：

- `docs/usage-and-ignore-guide-2026-03-12.md`

## 典型工作流

### 1. 创建文章骨架

这里有一个非常重要的预期说明：

- `xpost init` 只会生成 Markdown 骨架
- 不会自动根据主题写出完整正文
- `--style` 的作用是把对应 Prompt 写进文件顶部注释，方便后续交给 Claude / OpenClaw / Codex 继续生成成文

也就是说，正确理解应该是：

`topic + style -> 骨架 + Prompt -> 外部 LLM 生成完整正文 -> 自动配图 -> 发布`

```bash
xpost init content/drafts/your_article.md --topic "你的主题" --style zara
```

说明：

- 会自动创建 `content/drafts/images/`
- 会自动复制示例 `cover.png` 和 `demo1.png`
- 会在 Markdown 顶部写入 HTML 注释形式的 Prompt 元数据

### 2. 用 xpost 直接生成正文

`xpost init` 之后，可以直接让 `xpost generate` 调用本地配置的 LLM API，把占位正文扩写成正式文章。

```bash
xpost generate content/drafts/your_article.md
```

说明：

- 默认优先读取环境变量：
  - `XPOST_LLM_API_KEY`
  - `XPOST_LLM_API_URL`
  - `XPOST_LLM_MODEL`
- 这些变量现在也可以直接写在项目根目录 `.env` 中
- 默认模型优先使用 `claude-sonnet-4-6`
- 原骨架会先自动备份成 `*.skeleton.<timestamp>.md`

也可以覆盖输出路径：

```bash
xpost generate content/drafts/your_article.md --output content/drafts/your_article.generated.md
```

### 3. 也可以手动用 Claude / OpenClaw / Codex 生成正文

如果你想手工控制写作过程，也可以不用 `xpost generate`，而是把骨架交给 Claude / OpenClaw / Codex 继续扩写。

推荐操作：

1. 打开 `content/drafts/your_article.md`
2. 查看顶部 HTML 注释中的 Prompt
3. 把整份 Markdown 交给 Claude / OpenClaw / Codex
4. 让它基于该 Prompt 直接输出完整 Markdown 文章，覆盖占位段落

建议给同事或 Agent 的指令模板：

```text
请基于这份 Markdown 顶部的 Prompt，直接输出完整文章正文。
要求：
1. 保留 H1 标题
2. 保留图片占位位置和图片路径
3. 保留结尾链接结构
4. 替换掉所有模板占位句子，不要输出解释
```

### 4. 校验与解析 Markdown

```bash
xpost validate content/drafts/your_article.md
xpost parse content/drafts/your_article.md
```

说明：

- `validate` 只校验 Markdown 结构是否符合发布要求
- `parse` 只把 Markdown 解析成 JSON
- 这两个命令都不会生成正文

### 5. 使用多风格 Prompt 写文

内置 3 种写作风格：


| 风格     | 文件                               | 场景        |
| ------ | -------------------------------- | --------- |
| `zara` | `content/prompts/prompt_zara.md` | 经验分享、产品洞察 |
| `tech` | `content/prompts/prompt_tech.md` | 技术教程、架构分析 |
| `fun`  | `content/prompts/prompt_fun.md`  | 轻松科普、幽默表达 |


Prompt 使用说明见：

- `content/prompt-guide.md`

### 6. 自动配图

本地自动配图命令：

```bash
xpost auto-img content/drafts/your_article.md --style zara
```

说明：

- 该命令会扫描 Markdown 中的 `images/*.png` 占位符
- `images/cover.png` 会使用横幅封面图模板，强调 wide banner、居中主体、充足留白
- 其他 `images/*.png` 会使用正文示意图模板，强调 clean modern isometric illustration
- 会先使用文本 LLM 生成配图 brief，再调用 Gemini Flash Image 生成真实图片
- 图片会写回文章对应目录下的 `images/`
- `xpost generate` + `xpost auto-img` 可以组成完整的自动成文闭环

工作流文件：

- `.agent/workflows/auto-imgByMdCn.md`

如果你还想在 Antigravity 里手工跑这条工作流，也可以继续使用：

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

说明：

- 这是 Antigravity 集成能力
- 依赖 Antigravity 自身的 workflow 运行环境
- 仍然可以作为自动配图的人工兜底路径

### 7. 最小闭环：从主题到发布 Article

如果同事想走“主题/风格 -> 成文 -> 配图 -> 发布”的最小闭环，推荐直接按下面顺序操作：

```bash
xpost init content/drafts/your_article.md --topic "OpenClaw acp避坑指南" --style zara
```

然后：

1. 运行：

```bash
xpost generate content/drafts/your_article.md
```

如果你更想手工写作，也可以改为让 Claude / OpenClaw / Codex 基于顶部 Prompt 生成完整正文，覆盖模板占位内容

1. 自动配图：

```bash
xpost auto-img content/drafts/your_article.md --style zara
```

或者继续在 Antigravity 中执行：

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

1. 回到本地校验：

```bash
xpost validate content/drafts/your_article.md
```

1. 先保存草稿：

```bash
xpost publish content/drafts/your_article.md --no-wait
```

1. 确认没问题后再正式发布：

```bash
xpost publish content/drafts/your_article.md --publish --no-wait
```

更详细的团队操作说明见：

- `docs/article-minimal-loop-runbook-2026-03-13.md`

### 8. 发布 Article

保存草稿：

```bash
xpost publish content/examples/articleNew.md --no-wait
```

直接发布：

```bash
xpost publish content/examples/articleNew.md --publish --no-wait
```

### 9. 发布 Post

纯文本：

```bash
xpost post "Hello world" --publish
```

图文：

```bash
xpost post "This is an image post" --images /path/to/image.png --publish
```

### 10. 用 Grok 搜集热点

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --json-only
```

### 11. 用 xpost 统一入口运行 X 雷达

扫描：

```bash
xpost radar-scan
```

分析：

```bash
xpost radar-analyze --days 7
```

日报：

```bash
xpost radar-daily
```

周报：

```bash
xpost radar-weekly
```

账号管理：

```bash
xpost radar-accounts list
xpost radar-accounts add NewAccount "推荐原因"
xpost radar-accounts remove NewAccount
xpost radar-accounts restore NewAccount
```

Following 与 Radar 差异报表：

```bash
python xpost.py following-sync jackaiwison
```

默认输出：

- `xinfo/log/following/YYYY-MM-DD.json`
- `xinfo/log/following/myfollowing_latest.json`
- `xinfo/log/myfollowing.xlsx`（Summary / Following / Radar / GAP1 / GAP2）

完整性判断：

- `completion_status=complete` 表示采集数达到 X profile 上显示的 Following 数量。
- `completion_status=partial` 或 `partial_limited` 表示结果可看但不应用来直接批量增删。
- `completion_status=unknown` 表示未能读取预期 Following 总数，不能把 `complete` 当作已抓全。

结果文件说明：

- 最新扫描快照（每次覆盖）：
  - `xinfo/RESULT.json`
- 扫描明细与去重状态：
  - `xinfo/log/ideas.md`
  - `xinfo/log/.ideas_seen.json`
- 天级日志与分析结果：
  - `xinfo/log/day/YYYY-MM-DD.log`
  - `xinfo/log/day/YYYY-MM-DD_result.json`
  - `xinfo/log/day/YYYY-MM-DD_analysis.json`
- 天级日报正文：
  - `xinfo/log/day/YYYY-MM-DD.md`
- 周报正文：
  - `xinfo/log/week/YYYY-MM-DD.md`
- 周级趋势快照：
  - `xinfo/log/trends/YYYY-WW.json`

存储粒度说明：

- `RESULT.json`：最新一次扫描结果，不按天保留
- `day/*.log`：按天保留
- `day/*_result.json`：按天保留
- `day/*_analysis.json`：按天保留
- `day/*.md`：按天保留，保存日报正文
- `week/*.md`：按生成日期保留，保存周报正文
- `trends/*.json`：按周保留
- `ideas.md`：滚动保留最近几天内容，不是严格按天拆分

LLM 使用说明：

- 项目根目录 `.env` 支持本地配置：
  - `XPOST_LLM_API_KEY`
  - `XPOST_LLM_API_URL`
  - `XPOST_LLM_MODEL`
  - `XPOST_RADAR_LLM_MODEL`
- `radar-daily` 和 `radar-weekly` 默认走 TokenMax 的 Opus 路径
- 默认模型优先：`claude-opus-4-6`
- 如需覆盖，可传 `--model`
- `radar-scan` / `radar-analyze` 本身不依赖 LLM
- `xinfo/log/interests.json` 是雷达日报 / 周报筛选标准的核心文件，建议先同步为真实兴趣画像再运行

运行日志说明：

- `radar-daily` / `radar-weekly` 每次运行都会追加写入：
  - `xinfo/log/runtime/YYYY-MM-DD_radar-daily.jsonl`
  - `xinfo/log/runtime/YYYY-MM-DD_radar-weekly.jsonl`
- 日志会记录输入文件、输出文件、模型、尝试次数、错误信息和原始响应摘要，便于排查 LLM 返回格式问题

## 目录结构

```text
gitxPost/
├── xpost.py
├── auto_publish_uc.py
├── auto_publish_post.py
├── grok_hot_posts.py
├── browser_cdp_session.py
├── xinfo/
├── requirements.txt
├── pyproject.toml
├── CHANGELOG.md
├── README.md
├── CI/
├── docs/
├── skills/
│   ├── README.md
│   ├── xpost-cli/
│   ├── x-radar-cli/
│   ├── grok-hotposts-cli/
│   └── content-workflow/
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

当前 repo 级 skills 现在保留四类“正在使用的入口”：

- `skills/xpost-cli/SKILL.md`
  - 统一处理 Article / Post 的 CLI 工作流
- `skills/x-radar-cli/SKILL.md`
  - 统一处理 Radar 的 scan / analyze / daily / weekly / accounts
- `skills/grok-hotposts-cli/SKILL.md`
  - 处理 Grok 热点搜索
- `skills/content-workflow/SKILL.md`
  - 处理 Markdown 起稿、Prompt 选择、Antigravity 配图与发布前准备

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
- `docs/article-minimal-loop-runbook-2026-03-13.md`
- `docs/progress-summary-2026-03-12.md`

## Changelog 规则

项目要求：

- 每次准备 `git commit` 前，先更新 `CHANGELOG.md`
- 如果改动影响测试或交付信心，顺手更新 `CI/` 文档

规则文件：

- `.cursor/rules/changelog-before-commit.mdc`
