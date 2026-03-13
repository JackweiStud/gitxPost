# Article 最小闭环操作说明

日期：2026-03-13

这份文档用于解决一个常见误解：

- 同事希望输入“主题 + 风格”后，直接得到完整文章并发布
- 但当前项目的 `xpost init` 实际只会生成 Markdown 骨架，不会自动生成完整正文

所以，当前 `Article` 的最小闭环应该理解为：

`主题/风格 -> Markdown 骨架 + Prompt -> 外部 LLM 生成完整正文 -> Antigravity 自动配图 -> 校验 -> 发布`

## 1. 正确预期

`xpost init` 的作用：

- 创建一份结构正确的 Markdown 文章骨架
- 创建 `images/` 目录
- 复制示例 `cover.png` 和 `demo1.png`
- 在文件顶部写入与 `--style` 对应的 Prompt 注释

`xpost init` 不会做的事：

- 不会自动写出完整正文
- 不会自动替换模板占位句子
- 不会自动调用 Claude / OpenClaw / Codex 生成文章

## 2. 推荐最小闭环

### 第一步：生成骨架

```bash
xpost init content/drafts/your_article.md --topic "OpenClaw acp避坑指南" --style zara
```

成功后会得到：

- `content/drafts/your_article.md`
- `content/drafts/images/cover.png`
- `content/drafts/images/demo1.png`

## 3. 第二步：生成完整正文

打开刚生成的 Markdown 文件，可以看到顶部有 HTML 注释形式的 Prompt。

接下来把整份 Markdown 交给 Claude / OpenClaw / Codex，要求它：

- 基于顶部 Prompt 生成完整文章
- 保留标题
- 保留图片路径和图片占位位置
- 保留结尾链接结构
- 替换掉所有模板占位句子

推荐指令：

```text
请基于这份 Markdown 顶部的 Prompt，直接输出完整文章正文。
要求：
1. 保留 H1 标题
2. 保留图片占位位置和图片路径
3. 保留结尾链接结构
4. 替换掉所有模板占位句子
5. 不要输出解释，只输出最终 Markdown
```

## 4. 第三步：自动配图

在 Antigravity 中执行：

```bash
/auto-imgByMdCn.md content/drafts/your_article.md
```

说明：

- 这一步依赖 Antigravity 自身环境
- 如果配图失败，可以先手动补图，再继续下面步骤

## 5. 第四步：校验

```bash
xpost validate content/drafts/your_article.md
```

预期：

- `ok: true`
- 没有结构性错误

可选调试：

```bash
xpost parse content/drafts/your_article.md
```

`parse` 的作用只是把 Markdown 解析成 JSON，方便确认标题、封面图、内容图和 HTML 片段，不会生成正文。

## 6. 第五步：先保存草稿

```bash
xpost publish content/drafts/your_article.md --no-wait
```

建议团队先走草稿链路，确认：

- 标题是否正确
- 正文是否完整
- 封面图是否正确
- 内容图是否都能上传

## 7. 第六步：正式发布

确认草稿无误后，再执行：

```bash
xpost publish content/drafts/your_article.md --publish --no-wait
```

## 8. 为什么同事会误解

常见误解是把这条链路理解成：

`topic + style -> 自动写完整文章`

但当前项目实际能力是：

`topic + style -> 骨架 + Prompt`

因此，如果在 `init` 之后立刻做 `validate` 和 `parse`，你看到的只是：

- 结构正确
- 图片路径存在
- 占位内容还没被替换

这不是失败，而是因为“正文生成”这一步还没做。

## 9. 团队建议

如果是给同事使用，建议固定说法如下：

1. `xpost init` 是“起稿器”，不是“成文生成器”
2. 真正文需要 Claude / OpenClaw / Codex 补写
3. `validate` 和 `parse` 只做结构检查，不会写正文
4. 推荐始终先草稿，再正式发布

## 10. 当前最小闭环总结

```text
主题/风格
-> xpost init 生成骨架
-> Claude / OpenClaw / Codex 生成完整 Markdown 正文
-> Antigravity 自动配图
-> xpost validate
-> xpost publish --no-wait
-> xpost publish --publish --no-wait
```
