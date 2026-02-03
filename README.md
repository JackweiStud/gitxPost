# X Article OpenClaw Automation (GitxPost)

> **面向中长文创作者的 X (Twitter) Article 自动化发布工具**  
> _让写作回归 Markdown，让发布回归一键_

## 🚀 解决什么痛点？

在 X 上发布长文章 (Articles) 长期以来体验不够友好，创作者面临以下挑战：

1.  **排版丢失**：从 Notion、Obsidian 或其他编辑器直接复制到 X Article 编辑器，格式（粗体、标题、代码块）经常错乱或丢失。
2.  **图片插入繁琐**：X Article 不支持 Markdown 图片链接，也不支持直接批量粘贴混排图片。你需要一张张手动上传并拖动到正确位置。
3.  **重复劳动**：每次发布都需要重复 "打开浏览器 -> 登录 -> 复制 -> 粘贴 -> 调整 -> 发布" 的机械流程。
4.  **多账号管理难**：浏览器指纹和 Cookie 隔离管理麻烦，容易触发风控。

**OpenClawAuto/gitxPost** 正是为了解决这些问题而生。它能够读取标准的 Markdown 文件，自动渲染为富文本，并驱动隐身浏览器完成所有发布动作。

---

## ✨ 核心功能

*   **Markdown 原生支持**：支持标准 Markdown 语法（H1-H6, 粗体, 列表, 引用, 代码块, 链接）。
*   **智能图片处理**：自动识别 Markdown 中的本地图片路径，并在发布时自动定位插入到正确段落。
*   **反指纹自动化**：基于 Playwright 的隐身模式 (Stealth Mode)，模拟真实人类行为（鼠标轨迹、随机延迟、打字速度），通过 X 的机器人检测。
*   **独立环境镜像**：使用 `chrome_data_mirror` 技术，将登录状态与本机环境隔离，既保证了登录持久化，又避免了自动化脚本污染本机浏览器数据。
*   **双模式运行**：支持 **草稿预览模式**（默认）和 **自动发布模式** (`--publish`)。

---

## �️ 技术栈与依赖

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
├── � auto_publish.py        # [核心] 自动化发布主程序
├── � manual_login.bat       # [核心] 登录环境初始化脚本
├── � pyEnv.py               # 环境检测工具
├── � chrome_data_mirror/    # (自动生成) 浏览器用户数据镜像，用于保存 Session
├── 📂 pasreMarkDown/         # Markdown 解析与剪贴板工具模块
└── 📄 requirements.txt       # 项目依赖表
```

---

## 🚦 快速开始 (面向新开发者)

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

### 3. 发布文章
假设你的MD文档已写好（后续可以AI直接生产）
现在你可以运行自动化脚本了：

```powershell
# 1. 发布为草稿 (推荐测试用，脚本会自动停在发布前最后一步)
python auto_publish.py "D:\Path\To\Your\Article.md"

# 2. 直接发布 (慎用，会直接点击 Tweet)
python auto_publish.py "D:\Path\To\Your\Article.md" --publish
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

---

## 👨‍💻 开发者指南

如果你想修改代码：

*   **`auto_publish.py`**:
    *   `setup_stealth_browser()`: 负责浏览器启动参数，修改 `headless=True` 可后台运行（不推荐，容易被检测）。
    *   `HumanBehaviorSimulator`: 这里的参数控制模拟人类操作的随机延迟，调整它可以平衡速度与安全性。
    *   `auto_publish_article()`: 主业务逻辑流程。

---

> _OpenClawAuto - Automate the mundane, create the extraordinary._
