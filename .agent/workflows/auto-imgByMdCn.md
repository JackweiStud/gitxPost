---
description: 分析 Markdown 内容，使用 AI 生成匹配的插图，并替换占位符。
---

# 自动配图文章工作流

本工作流旨在指导 AI 智能体分析 Markdown 文件，理解每个图片占位符的上下文，生成高质量的 AI 图片，并自动完成替换工作。

## 1. 分析与提取
1.  **读取 Markdown 文件**：定位目标 `.md` 文件。
2.  **识别占位符**：检索所有格式为 `![alt text](images/filename.png)` 的图片标签。
3.  **上下文分析**：针对每个占位符，读取其周围的文本（前后段落），深入理解需要可视化的内容。
4.  **风格提取**：从文章元数据或正文中提取关键的视觉元素、情绪基调和配色方案。

## 2. 提示词 (Prompt) 构造策略
请使用以下公式为每张图片构建精准的绘画提示词（Prompt 建议保持英文以获得最佳效果）：
`[Subject/主体] + [Action/动作交互] + [Environment/环境] + [Art Style/风格] + [Color Palette/色调] + [Quality Modifiers/质量修饰]`

-   **主体 (Subject)**：源自 `alt text` 或直接上下文（例如："Robotic Claw", "Digital Bridge"）。
-   **风格 (Style)**：确保整篇文章配图风格统一（例如："High-tech", "Cyberpunk", "Minimalist Vector"）。
-   **色调 (Color)**：优先使用项目品牌色或文章设定的主色调（例如："Neon Blue and Purple"）。

## 3. 图片生成 (Turbo Mode)
对于每一个识别出的图片需求，调用 `generate_image` 工具进行生成。

**基于上下文的 Prompt 示例：**
-   *封面图*："A wide banner style futuristic cinematic shot of [Subject], [Action], [Style], [Lighting], wide 5:2 aspect ratio, ultra-wide angle, zoomed out, small subject centered, lots of negative space on top and bottom, central composition, essential subject in the middle horizontal strip, safe for cropping, no text."
-   *架构/示意图*："A clean, modern isometric illustration of [Concept], [Style], white background."

## 4. 执行与部署
1.  **生成**：根据构造的 Prompt 调用 `generate_image`。
2.  **移动与重命名**：将生成的图片文件（Artifacts）移动到文章对应的 `images/` 目录中，并重命名以匹配 Markdown 中的占位符路径。
    // turbo
    -   *命令*：`cp "[ArtifactPath]" "[LocalPath]"`
3.  **验证**：确认 Markdown 文件引用无误，图片显示正常。

## 5. 用户反馈
向用户展示生成结果，询问对风格和细节的反馈。如需调整，请微调 Prompt 并重新生成特定的图片。
