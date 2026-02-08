# X Article 自动发布工具 (macOS 专用版)

> **面向中长文创作者的 X (Twitter) Article 自动化发布工具**  
> _使用 undetected-chromedriver 反检测技术，让发布回归一键_

## 🚀 功能特性

- **Markdown 原生支持**：支持标准 Markdown 语法（标题、粗体、列表、引用、代码块）
- **智能图片处理**：自动识别本地图片并插入到正确位置
- **反检测技术**：基于 undetected-chromedriver，通过 X 的机器人检测
- **登录状态持久化**：登录一次，后续运行无需重复登录
- **双模式运行**：草稿预览模式（默认）和自动发布模式

---

## 🛠️ 技术栈

- **Python** 3.9+
- **undetected-chromedriver** - 反检测浏览器自动化
- **Chrome** 浏览器（macOS 系统安装）

---

## 📂 项目结构

```
gitxPost/
├── auto_publish_uc.py    # 核心发布脚本 (macOS 专用)
├── config.py             # 配置文件
├── pyEnv.py              # 环境检测工具
├── xpost.py              # CLI 入口（推荐给 Agent/自动化）
├── requirements.txt      # 项目依赖
├── chrome_data_mirror/   # 浏览器登录状态（自动生成）
├── CreateMd/             # 文章创作目录
│   ├── prompts/          # 多风格 Prompt 文件
│   └── images/           # 文章配图目录
├── pasreMarkDown/        # Markdown 解析模块
├── .agent/workflows/     # AI Agent 工作流
└── venv/                 # Python 虚拟环境
```

---

## 🚦 快速开始

### 1. 环境准备

确保已安装 **Python 3.9+** 和 **Chrome 浏览器**。

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 1.1 安装 CLI（推荐）

在虚拟环境中安装本地 CLI，之后可直接使用 `xpost` 命令：

```bash
cd /Users/jackwl/Code/gitcode/gitxPost
source venv/bin/activate
pip install -e .
xpost --help
```
你也可以使用一键脚本完成以上步骤：
```bash
./scripts/install_cli.sh
```

### 2. 首次登录（仅需一次）

```bash
# 激活虚拟环境
source venv/bin/activate

# 推荐：使用 CLI（会打开浏览器）
xpost publish CreateMd/your_article.md

# 或：直接运行脚本（等价）
python3 auto_publish_uc.py CreateMd/your_article.md
```

首次运行时，脚本会检测到未登录状态并提示你：
1. 在打开的 Chrome 浏览器中登录你的 X 账号
2. 完成所有安全验证
3. 登录成功后脚本自动继续

> 💡 登录状态会保存到 `chrome_data_mirror/` 目录，后续运行无需重新登录。

### 2.1 CLI 速查（推荐给 Agent/自动化）

所有命令输出 JSON，方便其他 Agent/LLM 调用。

```bash
# 生成文章骨架（可选指定主题/风格）
xpost init CreateMd/your_article.md --topic "你的主题" --style zara

# 发布前预检（严格按 CreateMd/template.md 约束）
xpost validate CreateMd/your_article.md

# 解析为结构化 JSON（title/cover/images/html 等）
xpost parse CreateMd/your_article.md

# 保存草稿（默认）或直接发布（输出包含 missing_images 与耗时）
xpost publish CreateMd/your_article.md
xpost publish CreateMd/your_article.md --publish

# 环境与依赖检查
xpost doctor
```

风格参数 `--style` 支持：`zara` / `tech` / `fun`（对应 `CreateMd/prompts/` 下的 Prompt）。

### 2.2 Agent 调用示例

示例脚本会执行 `init -> validate -> publish`（默认草稿），并打印每一步的 JSON 结果。可直接传入主题文本：

```bash
python3 scripts/agent_example.py "关于AI电力的问题文章"

# 或传入 Markdown 路径
python3 scripts/agent_example.py CreateMd/your_article.md
```

### 2.3 自动配图（Antigravity 工作流）

本项目内置 Antigravity 工作流：`.agent/workflows/auto-imgByMdCn.md`  
在 Antigravity 的对话中运行以下命令，可自动为指定 Markdown 插入配图：

```bash
/auto-imgByMdCn.md CreateMd/your_article.md
```

说明：该流程依赖 Antigravity 的 workflow 运行能力与其内置的图片生成工具，其他平台通常无法直接执行该工作流。

### 2.4 一键触发自动配图（Antigravity + AppleScript）

脚本会启动 Antigravity、打开本项目，并模拟输入命令：

```bash
./scripts/antigravity_auto_img.sh CreateMd/your_article.md
```

如果 Antigravity 的聊天输入快捷键不是 `cmd+l`，可通过环境变量覆盖：

```bash
AGY_FOCUS_SHORTCUT=cmd+shift+l ./scripts/antigravity_auto_img.sh CreateMd/your_article.md
```

首次运行可能需要在 macOS 中授权终端的“辅助功能”权限，否则无法模拟键盘输入。

### 3. 创作文章

在 `CreateMd/` 目录下创建 Markdown 文件，格式要求：

```markdown
# 文章标题（H1 级别，必需）

![封面图描述](images/cover.png)

开场段落...

## 章节一

内容段落...

![内容图片](images/demo1.png)

## 章节二

- 列表项 1
- 列表项 2

> 引用块：重点强调的内容

---

[@YourHandle](https://x.com/yourhandle)
```

**完整示例** (`CreateMd/my_article.md`)：

```markdown
# 我如何用 AI 在 30 秒内搞定周报

![封面图](images/cover.png)

写周报曾经是我周五最头疼的事。花一小时整理邮件？No thanks. 🙅‍♀️

## 发现

于是我试着把工作流丢给了 Claude...

- 痛点 1：以前要手动整理
- 痛点 2：格式还经常不对

结果？简直是魔法。✨

![对比图](images/demo1.png)

## 原理

> Mind = blown 🤯. 这完全改变了我的工作方式。

1. 第一步：把邮件导出
2. 第二步：丢给 AI 处理
3. 第三步：复制粘贴搞定

## 结语

别只看，去试试！🚀

---

[@YourHandle](https://x.com/yourhandle)
```

### 4. 发布文章

```bash
# 激活虚拟环境
source venv/bin/activate

# 发布为草稿（推荐）
python3 auto_publish_uc.py CreateMd/your_article.md

# 直接发布
python3 auto_publish_uc.py CreateMd/your_article.md --publish
```

---

## 🎨 多风格写作

内置 3 种写作风格 Prompt：

| 风格 | 文件 | 适用场景 |
|------|------|----------|
| Builder/洞察风 | `CreateMd/prompts/prompt_zara.md` | 经验分享、工具推荐 |
| 技术硬核风 | `CreateMd/prompts/prompt_tech.md` | 技术教程、架构分析 |
| 幽默风趣风 | `CreateMd/prompts/prompt_fun.md` | 科普、吐槽、轻松话题 |

---

## 🖼️ 配图工作流

使用 AI Agent 自动配图：

**工作流文件**：`.agent/workflows/auto-imgByMdCn.md`

**功能**：
1. 读取 Markdown 文件，识别图片占位符
2. 分析上下文，构造图片生成 Prompt
3. 调用 AI 图片生成工具
4. 自动保存到文章 `images/` 目录

---

## ⚠️ 常见问题

### Q1: 提示 "检测到未登录状态"？

**解决**：在打开的浏览器中手动登录即可，脚本会自动检测并继续。

### Q2: 登录状态过期了？

**解决**：删除 `chrome_data_mirror/` 目录，重新运行脚本并登录。

```bash
rm -rf chrome_data_mirror/
python3 auto_publish_uc.py CreateMd/your_article.md
```

### Q3: Chrome 版本不匹配？

**解决**：更新 `auto_publish_uc.py` 中的 `version_main` 参数为你的 Chrome 版本号。

```python
# 在 create_driver() 函数中修改
version_main=144  # 改为你的 Chrome 主版本号
```

查看 Chrome 版本：Chrome → 关于 Google Chrome

### Q4: 图片没插入成功？

**解决**：确保 Markdown 图片占位符格式正确，且前后有足够的文本段落。

---

## 👨‍💻 开发者指南

核心函数说明：

- **`create_driver()`** - 创建反检测浏览器实例
- **`check_login_status()`** - 检测登录状态
- **`input_title()`** - 自动输入文章标题
- **`paste_content()`** - 粘贴 HTML 格式内容
- **`insert_content_images()`** - 插入内容图片
- **`insert_cover_image()`** - 插入封面图

---

## 📝 注意事项

- 运行前请确保已关闭所有 Chrome 窗口
- 建议使用虚拟环境隔离项目依赖
- Chrome 版本更新后可能需要调整 `version_main` 参数

---

> _macOS 专用版 - 使用 undetected-chromedriver 反检测技术_
