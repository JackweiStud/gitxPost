# 需求文档：X Article 创作工作站

## 简介

X Article 创作工作站是一个完整的长文创作系统，支持从选题输入到发布的全流程工作。该系统集成现有的 `xpost.py` CLI 工具，提供 Web 界面来管理文章创作的各个阶段，包括骨架生成、AI 内容生成、Markdown 编辑、预览渲染和发布到 X 平台。

## 术语表

- **Article_Workstation**: X Article 创作工作站系统
- **Article**: X 平台的长文内容
- **Outline**: 文章骨架，包含标题和章节结构的 Markdown 文档
- **Draft**: 草稿状态的文章
- **Content**: 完整的文章内容（Markdown 格式）
- **CLI_Tool**: 现有的 xpost.py 命令行工具
- **Article_List_Page**: 文章列表页面
- **Article_Editor_Page**: 文章编辑器页面
- **Markdown_Preview**: Markdown 实时预览组件
- **Backend_API**: FastAPI 后端服务
- **Article_Storage**: 文章数据存储目录（xinfo/log/articles/）
- **Publish_Queue**: 发布队列系统

## 需求

### 需求 1：文章生命周期管理

**用户故事：** 作为内容创作者，我希望系统能够管理文章的完整生命周期，以便我可以追踪文章从创建到发布的所有状态。

#### 验收标准

1. THE Article_Workstation SHALL 支持以下文章状态：draft（草稿）和 published（已发布）
2. WHEN 用户创建新文章时，THE Article_Workstation SHALL 生成唯一的文章标识符（格式：art_<timestamp>）
3. THE Article_Workstation SHALL 记录文章的创建时间、更新时间和发布时间
4. WHEN 文章状态变更时，THE Article_Workstation SHALL 更新 updated_at 时间戳
5. THE Article_Workstation SHALL 将文章元数据存储为 JSON 格式文件在 Article_Storage 目录

### 需求 2：选题输入

**用户故事：** 作为内容创作者，我希望能够输入文章标题来开始创作流程，以便快速启动新文章项目。

#### 验收标准

1. THE Article_Editor_Page SHALL 提供标题输入表单字段
2. WHEN 用户提交标题时，THE Backend_API SHALL 验证标题非空
3. IF 标题为空，THEN THE Backend_API SHALL 返回错误消息
4. WHEN 标题验证通过时，THE Backend_API SHALL 创建新的 Article 记录
5. THE Article_Workstation SHALL 将当前步骤设置为 "title"

### 需求 3：骨架生成

**用户故事：** 作为内容创作者，我希望系统能够根据标题自动生成文章大纲，以便我有一个结构化的起点。

#### 验收标准

1. WHEN 用户请求生成骨架时，THE Backend_API SHALL 调用 CLI_Tool 的 init 命令
2. THE Backend_API SHALL 传递文章标题作为 --topic 参数给 CLI_Tool
3. WHEN CLI_Tool 成功生成骨架时，THE Backend_API SHALL 将 Outline 内容保存到 Article 记录
4. THE Backend_API SHALL 将 Outline 内容写入 Markdown 文件（路径：xinfo/log/articles/{article_id}.md）
5. THE Article_Workstation SHALL 将当前步骤更新为 "outline"
6. THE Article_Editor_Page SHALL 在编辑器中显示生成的 Outline
7. IF CLI_Tool 返回错误，THEN THE Backend_API SHALL 返回错误消息给前端

### 需求 4：骨架编辑

**用户故事：** 作为内容创作者，我希望能够手动编辑生成的文章骨架，以便调整文章结构以符合我的需求。

#### 验收标准

1. THE Article_Editor_Page SHALL 提供 Markdown 文本编辑器组件
2. THE Article_Editor_Page SHALL 在编辑器中加载当前的 Outline 内容
3. WHEN 用户修改 Outline 时，THE Article_Editor_Page SHALL 允许实时编辑
4. THE Article_Editor_Page SHALL 提供"重新生成"按钮来重新调用骨架生成
5. WHEN 用户点击"重新生成"时，THE Article_Workstation SHALL 覆盖现有 Outline

### 需求 5：全文内容生成

**用户故事：** 作为内容创作者，我希望 AI 能够根据骨架生成完整的文章内容，以便加速内容创作过程。

#### 验收标准

1. WHEN 用户请求生成全文时，THE Backend_API SHALL 调用 CLI_Tool 的 generate 命令
2. THE Backend_API SHALL 传递 Markdown 文件路径给 CLI_Tool
3. WHEN CLI_Tool 成功生成内容时，THE Backend_API SHALL 将 Content 保存到 Article 记录
4. THE Backend_API SHALL 更新 Markdown 文件内容
5. THE Article_Workstation SHALL 将当前步骤更新为 "content"
6. THE Article_Editor_Page SHALL 在编辑器中显示生成的 Content
7. IF CLI_Tool 返回错误，THEN THE Backend_API SHALL 返回错误消息给前端

### 需求 6：内容编辑

**用户故事：** 作为内容创作者，我希望能够手动编辑生成的文章内容，以便完善和个性化文章。

#### 验收标准

1. THE Article_Editor_Page SHALL 提供 Markdown 文本编辑器用于内容编辑
2. THE Article_Editor_Page SHALL 在编辑器中加载当前的 Content
3. WHEN 用户修改 Content 时，THE Article_Editor_Page SHALL 允许实时编辑
4. THE Article_Editor_Page SHALL 提供"保存草稿"按钮
5. WHEN 用户点击"保存草稿"时，THE Backend_API SHALL 保存 Content 到 Article 记录和 Markdown 文件
6. THE Article_Editor_Page SHALL 提供"重新生成"按钮来重新调用全文生成

### 需求 7：Markdown 预览

**用户故事：** 作为内容创作者，我希望能够实时预览 Markdown 渲染效果，以便查看文章的最终呈现效果。

#### 验收标准

1. THE Article_Editor_Page SHALL 提供 Markdown_Preview 组件
2. THE Markdown_Preview SHALL 使用 marked 库渲染 Markdown 内容为 HTML
3. WHEN 用户编辑 Content 时，THE Markdown_Preview SHALL 实时更新渲染结果
4. THE Markdown_Preview SHALL 支持代码高亮显示
5. THE Article_Editor_Page SHALL 提供左右分栏布局（左侧编辑器，右侧预览）

### 需求 8：文章发布

**用户故事：** 作为内容创作者，我希望能够将完成的文章发布到 X 平台，以便分享给我的读者。

#### 验收标准

1. THE Article_Editor_Page SHALL 提供"发布"按钮
2. WHEN 用户点击"发布"时，THE Backend_API SHALL 调用 CLI_Tool 的 publish 命令
3. THE Backend_API SHALL 传递 --publish 标志给 CLI_Tool
4. WHEN CLI_Tool 成功发布时，THE Backend_API SHALL 更新 Article 状态为 "published"
5. THE Backend_API SHALL 记录 published_at 时间戳
6. THE Backend_API SHALL 保存发布结果（包括文章 URL）到 Article 记录
7. IF CLI_Tool 返回错误，THEN THE Backend_API SHALL 返回错误消息给前端
8. WHEN 发布成功时，THE Article_Editor_Page SHALL 显示成功消息和文章 URL

### 需求 9：文章列表管理

**用户故事：** 作为内容创作者，我希望能够查看所有文章的列表，以便管理我的文章库。

#### 验收标准

1. THE Article_List_Page SHALL 显示所有文章的列表
2. THE Article_List_Page SHALL 显示每篇文章的标题、状态、创建时间和更新时间
3. THE Article_List_Page SHALL 按更新时间倒序排列文章
4. THE Article_List_Page SHALL 提供"新建文章"按钮
5. WHEN 用户点击"新建文章"时，THE Article_Workstation SHALL 导航到 Article_Editor_Page
6. THE Article_List_Page SHALL 为每篇文章提供"继续编辑"或"查看"按钮（根据状态）
7. THE Article_List_Page SHALL 为每篇文章提供"删除"按钮

### 需求 10：文章删除

**用户故事：** 作为内容创作者，我希望能够删除不需要的文章，以便保持文章库整洁。

#### 验收标准

1. WHEN 用户点击"删除"按钮时，THE Article_List_Page SHALL 显示确认对话框
2. WHEN 用户确认删除时，THE Backend_API SHALL 删除 Article 的 JSON 元数据文件
3. THE Backend_API SHALL 删除对应的 Markdown 文件
4. WHEN 删除成功时，THE Article_List_Page SHALL 从列表中移除该文章
5. IF 删除失败，THEN THE Backend_API SHALL 返回错误消息

### 需求 11：API 端点实现

**用户故事：** 作为前端开发者，我需要 RESTful API 端点来与后端交互，以便实现文章工作站的所有功能。

#### 验收标准

1. THE Backend_API SHALL 提供 GET /api/articles 端点返回文章列表
2. THE Backend_API SHALL 提供 POST /api/articles 端点创建新文章（接收 title 参数）
3. THE Backend_API SHALL 提供 GET /api/articles/{id} 端点获取单篇文章详情
4. THE Backend_API SHALL 提供 PUT /api/articles/{id} 端点更新文章内容（接收 content 参数）
5. THE Backend_API SHALL 提供 DELETE /api/articles/{id} 端点删除文章
6. THE Backend_API SHALL 提供 POST /api/articles/{id}/outline 端点生成骨架
7. THE Backend_API SHALL 提供 POST /api/articles/{id}/generate 端点生成全文
8. THE Backend_API SHALL 提供 POST /api/articles/{id}/publish 端点发布文章（接收 publish 布尔参数）
9. THE Backend_API SHALL 返回 JSON 格式响应，包含 ok 字段指示操作成功或失败
10. IF 操作失败，THEN THE Backend_API SHALL 在响应中包含 error 字段描述错误原因

### 需求 12：导航集成

**用户故事：** 作为用户，我希望能够从主导航访问文章工作站，以便快速进入文章管理界面。

#### 验收标准

1. THE Article_Workstation SHALL 在侧边栏导航中添加"文章"菜单项
2. WHEN 用户点击"文章"菜单项时，THE Article_Workstation SHALL 导航到 Article_List_Page
3. THE Article_Workstation SHALL 使用 📝 图标表示文章功能

### 需求 13：工作流步骤追踪

**用户故事：** 作为内容创作者，我希望系统能够记住我在创作流程中的位置，以便我可以从上次离开的地方继续。

#### 验收标准

1. THE Article_Workstation SHALL 追踪当前工作流步骤（title / outline / content / preview）
2. WHEN 用户重新打开文章时，THE Article_Editor_Page SHALL 显示对应步骤的界面
3. THE Article_Editor_Page SHALL 提供"上一步"和"下一步"按钮在步骤间导航
4. WHEN 用户点击"上一步"时，THE Article_Workstation SHALL 更新 step 字段并显示前一步骤界面
5. WHEN 用户点击"下一步"时，THE Article_Workstation SHALL 更新 step 字段并显示下一步骤界面

### 需求 14：错误处理

**用户故事：** 作为用户，我希望系统能够优雅地处理错误，以便我了解问题所在并采取相应措施。

#### 验收标准

1. WHEN Backend_API 遇到错误时，THE Backend_API SHALL 返回适当的 HTTP 状态码（4xx 客户端错误，5xx 服务器错误）
2. THE Backend_API SHALL 在响应中包含描述性错误消息
3. WHEN Article_Editor_Page 收到错误响应时，THE Article_Editor_Page SHALL 显示用户友好的错误消息
4. IF CLI_Tool 调用失败，THEN THE Backend_API SHALL 记录错误日志并返回错误响应
5. WHEN 文件操作失败时，THE Backend_API SHALL 返回文件系统错误消息

### 需求 15：数据持久化

**用户故事：** 作为内容创作者，我希望我的文章数据能够可靠地保存，以便我不会丢失创作内容。

#### 验收标准

1. THE Article_Workstation SHALL 将文章元数据存储在 xinfo/log/articles/{article_id}.json 文件
2. THE Article_Workstation SHALL 将文章 Markdown 内容存储在 xinfo/log/articles/{article_id}.md 文件
3. WHEN 保存文章时，THE Backend_API SHALL 原子性地写入文件（先写临时文件再重命名）
4. THE Backend_API SHALL 确保 Article_Storage 目录存在，如不存在则创建
5. THE Article_Workstation SHALL 在 JSON 文件中存储以下字段：id, title, status, created_at, updated_at, published_at, step, outline, content, md_path, publish_result

### 需求 16：CLI 工具集成

**用户故事：** 作为系统架构师，我希望系统能够正确集成现有的 xpost.py CLI 工具，以便复用已有的文章生成和发布逻辑。

#### 验收标准

1. THE Backend_API SHALL 通过 subprocess 模块调用 CLI_Tool
2. WHEN 调用 init 命令时，THE Backend_API SHALL 传递参数：md_path 和 --topic
3. WHEN 调用 generate 命令时，THE Backend_API SHALL 传递参数：md_path
4. WHEN 调用 publish 命令时，THE Backend_API SHALL 传递参数：md_path 和 --publish
5. THE Backend_API SHALL 捕获 CLI_Tool 的标准输出和标准错误
6. THE Backend_API SHALL 检查 CLI_Tool 的退出码以确定操作成功或失败
7. IF CLI_Tool 退出码非零，THEN THE Backend_API SHALL 将其视为错误

