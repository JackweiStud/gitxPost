# gitxPost

macOS 上的 X 自动化工具，当前包含两条独立链路：

- `Article`：将 Markdown 长文发布到 X Articles
- `Post`：发布 280 字符以内的短帖，可选带图
- `Grok Hot Posts`：通过 Grok 搜集 X 热门帖子并输出 JSON

## 当前状态

截至 2026-03-09，已经真实验证通过：

- `post` 纯文本发布
- `post` 单图发布
- `post` 草稿模式
- `article` 草稿链路

当前仍要注意：

- `post` 首次登录必须人工完成
- `post` 重点验证的是单图，多图建议继续专项回归
- `article` 和 `post` 的底层实现不同，不要混为一套

## 技术路线

### Article 链路

- 入口：[`xpost.py`](/Users/jackwl/Code/gitcode/gitxPost/xpost.py) 的 `publish`
- 核心实现：[`auto_publish_uc.py`](/Users/jackwl/Code/gitcode/gitxPost/auto_publish_uc.py)
- 技术：`undetected-chromedriver`
- 目标：X Articles 长文编辑器

### Post 链路

- 入口：[`xpost.py`](/Users/jackwl/Code/gitcode/gitxPost/xpost.py) 的 `post` / `post-login`
- 核心实现：[`auto_publish_post.py`](/Users/jackwl/Code/gitcode/gitxPost/auto_publish_post.py)
- 技术：真实 Google Chrome profile + Patchright CDP 附着
- 目标：X Post 短帖编辑器

### 热点搜索链路

- 入口：[`grok_hot_posts.py`](/Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py)
- 技术：`undetected-chromedriver` + 已登录 X 会话 + Grok
- 目标：按主题搜集 X 热门帖子并输出结构化 JSON

## 目录结构

```text
gitxPost/
├── xpost.py                         # CLI 主入口
├── auto_publish_uc.py              # Article 自动化主流程
├── auto_publish_post.py            # Post 自动化主流程
├── grok_hot_posts.py               # Grok 热门帖子搜集
├── config.py                       # Article 通用配置
├── requirements.txt                # 运行依赖
├── pyproject.toml                  # CLI 打包配置
├── pyEnv.py                        # 环境辅助脚本
├── .agent/workflows/               # Antigravity 工作流
├── CreateMd/                       # 文章创作目录
│   ├── template.md                 # 长文模板
│   ├── articleNew.md               # 示例文章
│   ├── prompts/                    # 写作风格 Prompt
│   ├── images/                     # 示例图片
│   └── testmd/                     # 旧测试文章样本
├── pasreMarkDown/                  # Markdown 解析与复制辅助
├── scripts/
│   ├── install_cli.sh              # 安装本地 CLI
│   └── agent_example.py            # Agent 调用示例
├── docs/
│   ├── x-post-implementation-overview-2026-03-09.md
│   ├── post-lessons-learned-2026-03-09.md
│   └── ...
├── memory/                         # 项目分析与复盘
├── chrome_data_mirror/             # 默认 Chrome 登录态目录
└── hot_posts_output/               # 热帖抓取输出
```

## 环境要求

- macOS
- Python 3.9+
- 已安装 Google Chrome
- 建议使用 `.venv`

## 安装

```bash
cd /Users/jackwl/Code/gitcode/gitxPost

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

说明：

- `requirements.txt` 包含 `patchright`
- `pyproject.toml` 主要用于本地 CLI 安装
- 如果只执行 `pip install -e .`，`post` 依赖不一定完整，所以建议先装 `requirements.txt`

## CLI 总览

```bash
xpost init ...
xpost validate ...
xpost parse ...
xpost publish ...
xpost post-login
xpost post ...
xpost doctor
```

所有命令都输出 JSON，便于 Agent 或脚本调用。

## Article 使用方式

### 1. 多风格写作

内置 3 种写作风格 Prompt：

| 风格 | 文件 | 适用场景 |
|------|------|----------|
| Builder/洞察风 | `CreateMd/prompts/prompt_zara.md` | 经验分享、工具推荐 |
| 技术硬核风 | `CreateMd/prompts/prompt_tech.md` | 技术教程、架构分析 |
| 幽默风趣风 | `CreateMd/prompts/prompt_fun.md` | 科普、吐槽、轻松话题 |

例如：

```bash
xpost init CreateMd/your_article.md --topic "你的主题" --style zara
```

### 2. 自动配图（Antigravity 工作流）

本项目内置 Antigravity 工作流：

- `.agent/workflows/auto-imgByMdCn.md`

在 Antigravity 的对话中运行以下命令，可自动为指定 Markdown 插入配图：

```bash
/auto-imgByMdCn.md CreateMd/your_article.md
```

这个流程会：

1. 读取 Markdown 文件，识别图片占位符
2. 分析上下文，构造图片生成 Prompt
3. 调用 AI 图片生成工具
4. 自动保存到文章 `images/` 目录

说明：

- 这个能力依赖 Antigravity 的 workflow 运行环境
- 当前仓库里可以确认工作流文件存在
- `scripts/antigravity_auto_img.sh` 这一层本地包装脚本当前不在仓库里，所以 README 不再把它写成现成命令入口

### 3. 写文章

按 [`CreateMd/template.md`](/Users/jackwl/Code/gitcode/gitxPost/CreateMd/template.md) 写 Markdown。  
示例可参考 [`CreateMd/articleNew.md`](/Users/jackwl/Code/gitcode/gitxPost/CreateMd/articleNew.md)。

### 4. 预检

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
xpost validate CreateMd/articleNew.md
```

### 5. 草稿或发布

```bash
# 草稿
xpost publish CreateMd/articleNew.md

# 直接发布
xpost publish CreateMd/articleNew.md --publish
```

说明：

- `article` 默认复用 [`chrome_data_mirror`](/Users/jackwl/Code/gitcode/gitxPost/chrome_data_mirror)
- 如果 X 未登录，会在浏览器里提示你人工登录
- 这条链路当前仍基于 `undetected-chromedriver`

## Post 使用方式

### 1. 首次初始化登录态

`post` 不再自动完成首次登录。正确方式是先执行：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
xpost post-login
```

然后在打开的真实 Chrome 里人工登录 X。登录成功后，状态会保存在默认 profile 里。

### 2. 发纯文本 Post

```bash
xpost post "Hello world" --publish
```

### 3. 发图文 Post

```bash
xpost post "这是一条图文 Post" --images /path/to/image.png --publish
```

### 4. 草稿模式

```bash
xpost post "先存草稿"
```

### 5. 可观察模式

调试时如果想看清楚输入、插图、点击过程：

```bash
xpost post "Visible flow" --images /path/to/image.png --publish --observe-ms 2500
```

## Post 参数

```bash
xpost post TEXT [--images ...] [--publish] [--profile-dir ...] [--no-wait] [--remote-debugging-port ...] [--observe-ms ...]
```

常用参数：

- `text`：Post 文本内容
- `--images`：最多 4 张图片
- `--publish`：直接发布，否则默认为草稿
- `--profile-dir`：自定义 Chrome profile
- `--no-wait`：完成后不等待
- `--remote-debugging-port`：真实 Chrome CDP 端口
- `--observe-ms`：关键步骤可观察停顿

`post-login` 参数：

- `--profile-dir`
- `--login-timeout`
- `--remote-debugging-port`

## doctor

检查环境：

```bash
xpost doctor
```

会输出：

- Python 版本
- Chrome 版本
- 关键依赖是否可用
- `post` 当前使用的浏览器控制方式

## X 热点搜索

项目还支持通过 Grok 搜索 X 热门帖子，核心脚本是：

- [`grok_hot_posts.py`](/Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py)

典型用途：

- 搜集 AI 热点
- 搜集科技动态
- 搜集某个主题过去若干小时内的热门帖子

基础用法：

```bash
source /Users/jackwl/Code/gitcode/gitxPost/.venv/bin/activate
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py --json-only
```

自定义主题、时间范围和数量：

```bash
python /Users/jackwl/Code/gitcode/gitxPost/grok_hot_posts.py \
  --topics AI 科技 开源Github \
  --hours 72 \
  --count 10 \
  --json-only
```

说明：

- 这条链路依赖已登录的 X 会话
- 需要具备 Grok 可用权限
- 结果会输出为 JSON，适合二次处理或给 Agent 消费
- 详细调用说明可参考 [`skills/grok-hotposts-cli/SKILL.md`](/Users/jackwl/Code/gitcode/gitxPost/skills/grok-hotposts-cli/SKILL.md)

## 设计说明

### 为什么 Post 不继续走 chromedriver

因为这次真实联调已经证明：

- Chrome 自动升级会频繁打断 `chromedriver`
- 运行时下载 driver 不稳定
- 首次登录在干净自动化浏览器里容易被 X 风控

所以 `post` 改成了：

- 人工在真实 Chrome 里登录一次
- 后续只自动化已登录后的发布动作

### 为什么 Article 仍保留旧链路

因为 Article 是已有老功能，当前已经能继续工作。  
这次的目标是修好 `post`，并确保不要再把 `article` 的登录态破坏掉。

## 相关文档

- [`docs/x-post-implementation-overview-2026-03-09.md`](/Users/jackwl/Code/gitcode/gitxPost/docs/x-post-implementation-overview-2026-03-09.md)
- [`docs/post-lessons-learned-2026-03-09.md`](/Users/jackwl/Code/gitcode/gitxPost/docs/post-lessons-learned-2026-03-09.md)
- [`docs/post-api-spec.md`](/Users/jackwl/Code/gitcode/gitxPost/docs/post-api-spec.md)

## 已知边界

- `post` 当前重点验证的是单图，不代表多图所有情况都已充分覆盖
- X 页面结构可能变化，后续建议为 `/home` 发帖入口补 fallback
- `article` 当前只再次验证了草稿链路

## 推荐维护原则

- 不要把 `article` 和 `post` 强行统一到底层实现
- `post` 优先保真实 Chrome profile 复用
- 修改浏览器启动逻辑后，必须同时回归 `article` 和 `post`
