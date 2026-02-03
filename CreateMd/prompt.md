# 文章生成 Prompt 选择

## 📚 可用风格

| 风格 | 文件 | 描述 | 适用场景 |
|---|---|---|---|
| **Builder/洞察风** (默认) | [prompt_zara.md](prompts/prompt_zara.md) | 硅谷创业者，Building in Public | 经验分享、工具推荐、效率提升 |
| **技术硬核风** | [prompt_tech.md](prompts/prompt_tech.md) | 资深工程师，深度技术分析 | 技术教程、架构分析、性能优化 |
| **幽默风趣风** | [prompt_fun.md](prompts/prompt_fun.md) | 段子手，轻松有趣科普 | 科普、吐槽、轻松话题 |

---

## 🚀 使用说明

### Step 1: 选择风格
根据你要写的内容类型，选择对应的 Prompt 文件。

### Step 2: 复制 Prompt
打开对应的 `.md` 文件，复制全部内容到 LLM 对话 (Claude/GPT/etc.)。

### Step 3: 填入主题
在 Prompt 的 `## 任务` 部分，将 `[在这里填入你的主题]` 替换为你的实际主题。

### Step 4: 生成文章
让 LLM 生成完整的 Markdown 文章。

### Step 5: 配图 (可选)
使用 `/auto-imgByMdCn` 工作流自动为文章配图。

### Step 6: 发布
使用 `auto_publish.py` 自动发布到 X。

```bash
python auto_publish.py <your_article.md> --publish
```

---

## ⚡ 快捷方式

如果你只想使用默认风格 (Builder/洞察风)，直接使用：

👉 [prompt_zara.md](prompts/prompt_zara.md)

---

## 📋 格式规范

所有风格都必须满足以下格式，确保自动发布脚本正常工作：

1. `# 标题` - H1 标题
2. `![封面](images/cover.png)` - 第一张图片作为封面
3. `![配图](images/xxx.png)` - 使用相对路径
4. 标准 Markdown 语法

详细规范请参考：[template.md](template.md)

---

## 🔍 验证

生成文章后，可运行以下命令验证格式：

```bash
python pasreMarkDown/skills/x-article-publisher/scripts/parse_markdown.py <your_article.md> --output json
```
