# X Article OpenClaw Automation (GitxPost)

> **面向中长文创作者的 X (Twitter) Article 自动化发布工具**  
> _让写作回归 Markdown，让发布回归一键_

## 🚀 解决什么痛点？

在 X 上发布长文章 (Articles) 长期以来体验不够友好，创作者面临以下挑战：

1.  **排版丢失**：从 Notion、Obsidian 或其他编辑器直接复制到 X Article 编辑器，格式（粗体、标题、代码块）经常错乱或丢失。
2.  **图片插入繁琐**：X Article 不支持 Markdown 图片链接，也不支持直接批量粘贴混排图片。你需要一张张手动上传并拖动到正确位置。
3.  **重复劳动**：每次发布都需要重复 "打开浏览器 -> 登录 -> 复制 -> 粘贴 -> 调整 -> 发布" 的机械流程。
4.  **内容风格单一**：长期使用同一写作风格，导致 X 上的内容千篇一律。

**OpenClawAuto/gitxPost** 正是为了解决这些问题而生。它能够读取标准的 Markdown 文件，自动渲染为富文本，并驱动隐身浏览器完成所有发布动作。

---

## ✨ 核心功能

*   **Markdown 原生支持**：支持标准 Markdown 语法（H1-H6, 粗体, 列表, 引用, 代码块, 链接）。
*   **智能图片处理**：自动识别 Markdown 中的本地图片路径，并在发布时自动定位插入到正确段落。
*   **多风格写作支持**：内置 3 种写作风格 Prompt，避免内容千篇一律。
*   **AI 配图工作流**：支持自动分析文章内容并生成配图。
*   **反指纹自动化**：基于 Playwright 的隐身模式 (Stealth Mode)，模拟真实人类行为（鼠标轨迹、随机延迟、打字速度），通过 X 的机器人检测。
*   **独立环境镜像**：使用 `chrome_data_mirror` 技术，将登录状态与本机环境隔离，既保证了登录持久化，又避免了自动化脚本污染本机浏览器数据。
*   **双模式运行**：支持 **草稿预览模式**（默认）和 **自动发布模式** (`--publish`)。

---

## 🎨 多风格写作支持

内置 3 种写作风格 Prompt，让你的内容更加多样化：

| 风格 | 文件 | 描述 | 适用场景 |
|---|---|---|---|
| **Builder/洞察风** | `CreateMd/prompts/prompt_zara.md` | 硅谷创业者，Building in Public | 经验分享、工具推荐 |
| **技术硬核风** | `CreateMd/prompts/prompt_tech.md` | 资深工程师，深度技术分析 | 技术教程、架构分析 |
| **幽默风趣风** | `CreateMd/prompts/prompt_fun.md` | 段子手，轻松有趣科普 | 科普、吐槽、轻松话题 |

### 使用方式

1. 选择适合的风格 Prompt 文件
2. 复制 Prompt 到 LLM (Claude/GPT/Grok)
3. 填入你的主题，生成文章
4. 使用配图工作流添加图片
5. 运行发布脚本

详细说明：[CreateMd/prompt.md](CreateMd/prompt.md)

---

## 🖼️ 配图工作流

支持自动分析文章并生成配图：

**工作流文件**：`.agent/workflows/auto-imgByMdCn.md`

**功能**：
1. 读取 Markdown 文件，识别图片占位符
2. 分析上下文，构造图片生成 Prompt
3. 调用 AI 图片生成工具
4. 自动保存到文章 `images/` 目录

---

## 🛠️ 技术栈与依赖

*   **语言**: Python 3.9+ (Windows 环境推荐)
*   **核心库**:
    *   `playwright`: 驱动 Chromium 内核进行网页操作
    *   `markdown`: 解析文章内容
    *   `pywin32`: 负责 Windows 系统剪贴板交互 (HTML/Image)
    *   `Pillow`: 图片处理
*   **脚本**: Windows Batch (`.bat`) 辅助环境管理

---

## 📂 项目结构

```text
D:\CODE\OpenClawAuto\gitxPost\
├── 🐍 auto_publish.py        # [核心] 自动化发布主程序
├── 🦇 manual_login.bat       # [核心] 登录环境初始化脚本
├── 🐍 pyEnv.py               # 环境检测工具
├── 📁 chrome_data_mirror/    # (自动生成) 浏览器用户数据镜像
├── 📂 CreateMd/              # 文章创作目录
│   ├── prompt.md             # 风格选择指引
│   ├── template.md           # 格式规范
│   ├── prompts/              # 多风格 Prompt 文件
│   │   ├── prompt_zara.md    # Builder/洞察风
│   │   ├── prompt_tech.md    # 技术硬核风
│   │   └── prompt_fun.md     # 幽默风趣风
│   └── images/               # 文章配图目录
├── 📂 pasreMarkDown/         # Markdown 解析与剪贴板工具模块
├── 📂 .agent/workflows/      # AI Agent 工作流
│   └── auto-imgByMdCn.md     # 自动配图工作流
└── 📄 requirements.txt       # 项目依赖表
```

---

## 🚦 快速开始

### 1. 环境准备

确保你已安装 Python 3.9+ 和 Chrome 浏览器。

```powershell
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
playwright install chromium
```

### 2. 账号准备 (首次运行必读) 🔑

为了避免自动化脚本在登录过程中被 X 风控拦截，我们采用 **"手动登录，自动继承"** 的策略。

1.  双击运行项目根目录下的 **`manual_login.bat`**。
2.  脚本会自动创建一个干净的浏览器镜像环境并打开 Chrome。
3.  在打开的浏览器中，**手动登录你的 X 账号**。
4.  登录成功并看到时间线后，**直接关闭浏览器窗口**。
    *   *原理：此时你的登录 Cookie 已被保存到 `chrome_data_mirror` 文件夹中。*

### 3. 创作文章

**方式一：使用多风格 Prompt**

```powershell
# 1. 选择风格 (打开对应的 Prompt 文件)
code CreateMd/prompts/prompt_zara.md

# 2. 复制 Prompt 到 LLM，填入主题，生成 Markdown 文章
# 3. 保存到 CreateMd/ 目录
```

**方式二：直接编写 Markdown**

参考格式规范：[CreateMd/template.md](CreateMd/template.md)

### 4. 配图 (可选)

使用 AI Agent 配图工作流，或手动准备图片放入 `images/` 目录。

### 5. 发布文章

```powershell
# 发布为草稿 (推荐测试用)
python auto_publish.py "CreateMd/your_article.md"

# 直接发布
python auto_publish.py "CreateMd/your_article.md" --publish
```

---

## ⚠️ 常见问题与风控

### Q1: 脚本提示 "检测到未登录状态"？
**原因**：Cookie 过期或之前的镜像数据损坏。
**解决**：
1.  脚本会自动删除旧的 `chrome_data_mirror` 文件夹。
2.  你只需要重新运行 `manual_login.bat`，重新登录一次即可。

### Q2: 为什么不直接在脚本里自动登录？
**回答**：X 的登录过程包含复杂的机器人验证（Cloudflare turnstile 等），自动化通过率极低且风险极高。手动登录一次保质期很长，是最安全高效的方案。

### Q3: 图片没插入进去？
**回答**：脚本依赖于占位符或文本定位。请确保 Markdown 图片前后有足够的文本段落。尽量避免将多张图片紧挨着放在一起，中间最好隔一行文字。

### Q4: 如何切换写作风格？
**回答**：打开 `CreateMd/prompts/` 目录，选择对应风格的 Prompt 文件，复制到 LLM 使用即可。

---

## 👨‍💻 开发者指南

如果你想修改代码：

*   **`auto_publish.py`**:
    *   `setup_stealth_browser()`: 负责浏览器启动参数，修改 `headless=True` 可后台运行（不推荐，容易被检测）。
    *   `HumanBehaviorSimulator`: 这里的参数控制模拟人类操作的随机延迟，调整它可以平衡速度与安全性。
    *   `auto_publish_article()`: 主业务逻辑流程。

*   **`CreateMd/prompts/`**:
    *   每个 Prompt 文件都是独立的，可以自由添加新风格。
    *   修改需遵循 `template.md` 的格式规范以确保自动发布兼容。

---

> _OpenClawAuto - Automate the mundane, create the extraordinary._
