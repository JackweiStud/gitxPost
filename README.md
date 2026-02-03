# X Article Publisher - Windows 版本

> 一键将 Markdown 文章发布到 X (Twitter) Articles，Windows 环境完全支持！

## 🎯 快速开始

### 1. 环境检查

```powershell
# 检查 Python 版本（需要 3.9+）
python --version

# 检查已安装的依赖
pip list | findstr /i "Pillow pywin32 clip-util playwright"
```

### 2. 快速测试

```powershell
# 方式一：使用批处理脚本（推荐）
quick_test.bat

# 方式二：直接运行测试
python test_manual_publish.py test_article_with_images.md
```

### 3. 发布你的文章

```powershell
# 创建你的 Markdown 文件
notepad my_article.md

# 测试发布
python test_manual_publish.py my_article.md
```

## 📁 项目文件说明

```
D:\CODE\OpenClawAuto\xPost\
├── 📄 README.md                        # 本文件
├── 📄 WINDOWS_GUIDE.md                 # 详细使用指南
├── 📄 PROJECT_SUMMARY.md               # 项目学习总结
│
├── 🔧 quick_test.bat                   # 快速测试脚本
├── 🐍 test_manual_publish.py           # 手动测试脚本
├── 🐍 test_playwright_publish.py       # 自动化脚本
│
├── 📝 test_article.md                  # 简单测试文章
├── 📝 test_article_with_images.md      # 带图片测试文章
│
├── 📂 images/                          # 测试图片
│   ├── cover.png
│   └── workflow.png
│
└── 📂 x-article-publisher-skill/       # 原始项目
    └── skills/x-article-publisher/
        ├── SKILL.md
        └── scripts/
            ├── parse_markdown.py       # Markdown 解析
            ├── copy_to_clipboard.py    # 剪贴板操作
            └── table_to_image.py       # 表格转图片
```

## 🚀 三种使用方式

### 方式一：全自动发布 🤖（推荐）

**适合场景**: 追求效率，批量发布

```powershell
# 自动发布（保存为草稿）
python auto_publish.py your_article.md

# 自动发布并直接发布
python auto_publish.py your_article.md --publish
```

**流程**:
1. 自动打开浏览器（使用你的 Chrome 配置）
2. 自动输入标题
3. 自动粘贴内容
4. 自动插入所有图片（封面图 + 内容图片）
5. 你只需最后点击"发布"

**特点**:
- ⚡ 最快（~3 分钟）
- 🛡️ 反机器人检测
- 🎭 人类行为模拟
- 🔥 页面预热机制
- ⏱️ 随机延迟

**反机器人机制**:
- 禁用 AutomationControlled 标记
- 覆盖 navigator.webdriver 属性
- 模拟真实打字速度（50-150ms/字符）
- 随机思考停顿（10% 概率）
- 平滑鼠标移动轨迹
- 渐进式页面滚动

### 方式二：手动测试（推荐新手）

**适合场景**: 学习和理解项目原理

```powershell
python test_manual_publish.py your_article.md
```

**流程**:
1. 脚本解析 Markdown
2. 两步复制流程：
   - 步骤 1：复制封面图 → 粘贴
   - 步骤 2：复制文章内容 → 粘贴
   - 步骤 3：交互式复制内容图片
3. 手动打开 https://x.com/compose/articles
4. 按提示粘贴内容
5. 手动发布

**优点**: 安全、可控、易于理解

### 方式三：Playwright 半自动化

**适合场景**: 需要更多控制权

```powershell
python test_playwright_publish.py your_article.md
```

**流程**:
1. 自动打开浏览器
2. 自动填充标题和内容
3. 手动插入图片
4. 手动确认发布

**优点**: 效率高、仍可人工审核

## ✨ 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| Markdown 解析 | ✅ | 支持标题、粗体、斜体、链接、列表、引用 |
| 图片处理 | ✅ | 自动上传封面和内容图片 |
| 富文本粘贴 | ✅ | 保留所有格式 |
| Block-Index 定位 | ✅ | 精确定位图片位置 |
| Windows 剪贴板 | ✅ | 支持 HTML 和图片 |
| 图片压缩 | ✅ | 可选质量参数 |

## 📚 文档导航

- **[QUICK_START.md](doc/QUICK_START.md)** - 🚀 5 分钟快速开始
  - 三种使用方式对比
  - Markdown 格式要求
  - 实战演练步骤
  - 常见问题解答

- **[AUTO_PUBLISH_GUIDE.md](doc/AUTO_PUBLISH_GUIDE.md)** - 📖 完整使用指南
  - 功能特性详解
  - 反机器人机制说明
  - 安装和配置
  - 故障排除
  - 最佳实践

- **[PROJECT_SUMMARY.md](doc/PROJECT_SUMMARY.md)** - 📊 项目总结
  - 完成功能清单
  - 技术架构说明
  - 性能对比分析
  - 未来开发计划

- **[WINDOWS_GUIDE.md](doc/WINDOWS_GUIDE.md)** - 🪟 Windows 环境指南
  - 环境配置
  - 详细使用方式
  - 常见问题
  - 学习路径

- **[config.py](config.py)** - ⚙️ 配置文件
  - 延迟时间配置
  - 人类行为参数
  - 浏览器配置
  - 图片质量设置

## 🎓 学习路径

### 第一阶段：理解和测试 ✅

- [x] 安装依赖
- [x] 运行测试脚本
- [x] 理解工作流程
- [x] 手动发布一篇文章

### 第二阶段：深入学习

- [ ] 阅读核心代码
- [ ] 理解 Block-Index 算法
- [ ] 测试各种 Markdown 语法
- [ ] 自定义图片处理参数

### 第三阶段：扩展功能

- [ ] 添加新的 Markdown 语法支持
- [ ] 优化 Playwright 脚本
- [ ] 支持批量发布
- [ ] 适配其他平台

### 第四阶段：形成能力

- [ ] 创建自己的自动化工具
- [ ] 分享经验和改进
- [ ] 贡献代码到开源社区

## 💡 使用技巧

### 1. 快速测试

```powershell
# 使用批处理脚本
quick_test.bat
```

### 2. 调试解析

```powershell
# 查看解析结果
python x-article-publisher-skill/skills/x-article-publisher/scripts/parse_markdown.py your_article.md

# 只看 HTML
python x-article-publisher-skill/skills/x-article-publisher/scripts/parse_markdown.py your_article.md --html-only
```

### 3. 测试剪贴板

```powershell
# 测试 HTML
python x-article-publisher-skill/skills/x-article-publisher/scripts/copy_to_clipboard.py html "<h1>测试</h1>"

# 测试图片
python x-article-publisher-skill/skills/x-article-publisher/scripts/copy_to_clipboard.py image images/cover.png --quality 85
```

## ❓ 常见问题

### Q: 需要什么订阅？

A: X Premium Plus 订阅（Articles 功能专属）

### Q: 支持哪些 Markdown 语法？

A: 标题、粗体、斜体、链接、引用、列表、图片、代码块

### Q: 图片格式有限制吗？

A: 支持 jpg, png, gif, webp，建议不超过 5MB

### Q: 可以批量发布吗？

A: 目前不支持，但可以通过脚本扩展实现

### Q: 如何调试 Playwright 脚本？

A: 修改 `headless=False` 可以看到浏览器操作过程

## 🔗 相关链接

- **原项目**: https://github.com/wshuyi/x-article-publisher-skill
- **X Articles**: https://x.com/compose/articles
- **Playwright**: https://playwright.dev/python/
- **Markdown**: https://www.markdownguide.org/

## 📊 性能对比

| 操作 | 手动 | 自动化 | 提升 |
|------|------|--------|------|
| 格式转换 | 15-20 分钟 | 0 秒 | ∞ |
| 图片上传 | 5-10 分钟 | 1 分钟 | 5-10x |
| **总计** | **20-30 分钟** | **2-3 分钟** | **10x** |

## 🎉 完成状态

- ✅ Windows 环境配置完成
- ✅ 核心功能测试通过
- ✅ 测试文件和脚本创建完成
- ✅ 完整文档编写完成
- ✅ 可以开始实际使用

## 🚀 下一步

1. **阅读** [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) 了解详细使用方法
2. **运行** `quick_test.bat` 快速体验
3. **创建** 你自己的 Markdown 文章
4. **发布** 到 X Articles
5. **学习** [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) 深入理解

## 📝 许可证

MIT License - 见原项目 LICENSE 文件

## 🙏 致谢

- 原项目作者: [wshuyi](https://github.com/wshuyi)
- 贡献者: [sugarforever](https://github.com/sugarforever)

---

**开始你的自动化发布之旅吧！** 🚀

如有问题，请查看 [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) 或 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
