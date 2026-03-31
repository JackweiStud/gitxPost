# 实施计划：X Article 创作工作站

## 概述

本实施计划按照"后端优先，前端跟进"的策略，分 6 个阶段完成 X Article 创作工作站的开发。系统将提供从选题输入到发布的完整工作流，集成现有的 xpost.py CLI 工具，通过 WebSocket 实现实时状态更新。

## 实施策略

1. **WebSocket 公共管理器优先**：先实现通用的 WebSocketManager 类，重构现有队列 WebSocket，再实现文章 WebSocket
2. **后端优先**：先完成所有后端 API 和 WebSocket 端点
3. **前端跟进**：后端稳定后再实现前端页面和组件
4. **增量验证**：每个阶段完成后进行集成测试

## 任务列表

### Phase 1: 基础架构和数据存储

- [x] 1. 实现文章数据存储层
  - [x] 1.1 创建文章存储目录结构
    - 在 `xinfo/log/` 下创建 `articles/` 目录
    - 实现目录自动创建逻辑
    - _Requirements: 15.4_
  
  - [x] 1.2 实现文章 ID 生成函数
    - 实现 `_generate_article_id()` 函数，格式为 `art_<timestamp_ms>`
    - 确保 ID 唯一性（使用毫秒级时间戳）
    - _Requirements: 1.2_
  
  - [x] 1.3 实现文章 JSON 元数据读写
    - 实现 `_read_article(article_id)` 函数读取 JSON 文件
    - 实现 `_write_article(article_id, data)` 函数原子性写入 JSON
    - 使用临时文件 + 重命名策略确保原子性
    - _Requirements: 1.5, 15.1, 15.3_
  
  - [x] 1.4 实现文章 Markdown 文件读写
    - 实现 `_read_article_content(article_id)` 函数读取 .md 文件
    - 实现 `_write_article_content(article_id, content)` 函数写入 .md 文件
    - 同样使用原子性写入策略
    - _Requirements: 15.2_
  
  - [x] 1.5 实现文章列表查询函数
    - 实现 `_list_articles()` 函数扫描 articles/ 目录
    - 按 updated_at 倒序排列
    - 返回文章元数据列表
    - _Requirements: 9.3_

- [x] 2. Checkpoint - 验证数据存储层
  - 编写单元测试验证文章 CRUD 操作
  - 测试原子性写入（中断写入不会损坏数据）
  - 测试并发读写安全性
  - 确保所有测试通过，询问用户是否继续

### Phase 2: WebSocket 公共管理器和重构

- [x] 3. 实现 WebSocket 公共管理器
  - [x] 3.1 创建 WebSocketManager 类
    - 在 `web/api/server.py` 中实现 `WebSocketManager` 类
    - 实现 `__init__(name)` 初始化方法
    - 实现 `connect(websocket)` 方法接受并注册连接
    - 实现 `disconnect(websocket)` 方法断开并清理连接
    - 实现 `broadcast(message)` 方法广播消息到所有连接
    - 实现 `close_all()` 方法关闭所有连接
    - 添加连接数日志和错误处理
    - _Requirements: Architecture requirement_
  
  - [ ]* 3.2 编写 WebSocketManager 单元测试
    - 测试连接管理（添加/移除连接）
    - 测试消息广播
    - 测试断开连接的自动清理
    - 测试并发连接场景
  
  - [x] 3.3 重构现有队列 WebSocket 使用 WebSocketManager
    - 创建 `_queue_ws_manager = WebSocketManager("Queue")` 实例
    - 重构 `websocket_queue()` 端点使用 `_queue_ws_manager.connect()`
    - 重构 `_broadcast_queue_update()` 使用 `_queue_ws_manager.broadcast()`
    - 在 `shutdown_event()` 中调用 `_queue_ws_manager.close_all()`
    - 验证现有队列功能不受影响
    - _Requirements: Architecture requirement_
  
  - [x] 3.4 实现文章 WebSocket 管理器实例
    - 创建 `_article_ws_manager = WebSocketManager("Article")` 实例
    - 实现 `websocket_articles()` WebSocket 端点
    - 实现 `_broadcast_article_update(event_type, article_id, data)` 函数
    - 在 `shutdown_event()` 中添加 `_article_ws_manager.close_all()`
    - _Requirements: Architecture requirement_

- [x] 4. Checkpoint - 验证 WebSocket 管理器
  - 测试队列 WebSocket 重构后功能正常
  - 测试文章 WebSocket 连接和断开
  - 测试消息广播到多个客户端
  - 确保所有测试通过，询问用户是否继续

### Phase 3: 核心 API 端点实现

- [ ] 5. 实现文章 CRUD API 端点
  - [ ] 5.1 实现 POST /api/articles 创建文章
    - 验证 title 非空（Requirements 2.2, 2.3）
    - 生成唯一 article_id
    - 创建初始 JSON 元数据（status=draft, step=title）
    - 设置 created_at 和 updated_at 时间戳
    - 返回 article_id 和 title
    - _Requirements: 1.1, 1.2, 1.3, 2.4, 2.5, 11.2_
  
  - [ ] 5.2 实现 GET /api/articles 获取文章列表
    - 调用 `_list_articles()` 获取所有文章
    - 按 updated_at 倒序排列
    - 返回文章列表（不包含 content 字段）
    - _Requirements: 9.1, 9.2, 9.3, 11.1_
  
  - [ ] 5.3 实现 GET /api/articles/{id} 获取文章详情
    - 读取 JSON 元数据和 Markdown 内容
    - 返回完整文章对象（包含 content）
    - 文章不存在时返回 404
    - _Requirements: 11.3_
  
  - [ ] 5.4 实现 PUT /api/articles/{id} 更新文章内容
    - 接收 content 参数
    - 更新 JSON 元数据和 Markdown 文件
    - 更新 updated_at 时间戳
    - 返回更新后的 updated_at
    - _Requirements: 6.5, 11.4_
  
  - [ ] 5.5 实现 DELETE /api/articles/{id} 删除文章
    - 删除 JSON 元数据文件
    - 删除 Markdown 文件
    - 返回成功响应
    - 文章不存在时返回 404
    - _Requirements: 10.2, 10.3, 11.5_
  
  - [ ]* 5.6 编写 CRUD API 集成测试
    - 测试创建文章（有效和无效标题）
    - 测试获取文章列表和详情
    - 测试更新文章内容
    - 测试删除文章
    - 测试错误处理（404, 400）

- [ ] 6. 实现文章工作流 API 端点
  - [ ] 6.1 实现 POST /api/articles/{id}/outline 生成骨架
    - 验证文章存在且 step=title
    - 立即返回 202 Accepted 响应
    - 启动后台异步任务调用 `xpost init --topic <title>`
    - 广播 WebSocket 事件 `article_outline_generating`
    - 成功后更新 step=outline，保存内容，广播 `article_outline_generated`
    - 失败时广播 `article_error`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.6, 16.1, 16.2_
  
  - [ ] 6.2 实现 POST /api/articles/{id}/generate 生成全文
    - 验证文章存在且 step=outline
    - 立即返回 202 Accepted 响应
    - 启动后台异步任务调用 `xpost generate <md_path>`
    - 广播 WebSocket 事件 `article_content_generating`
    - 成功后更新 step=content，保存内容，广播 `article_content_generated`
    - 失败时广播 `article_error`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 11.7, 16.1, 16.3_
  
  - [ ] 6.3 实现 POST /api/articles/{id}/publish 发布文章
    - 验证文章存在且 step=content 或 preview
    - 立即返回 202 Accepted 响应
    - 启动后台异步任务调用 `xpost publish <md_path> --publish`
    - 广播 WebSocket 事件 `article_publishing`
    - 成功后更新 status=published，设置 published_at，保存 article_url，广播 `article_published`
    - 失败时广播 `article_error`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.8, 16.1, 16.4_
  
  - [ ]* 6.4 编写工作流 API 集成测试
    - 测试完整工作流：create → outline → generate → publish
    - 测试 WebSocket 事件顺序和内容
    - 测试 CLI 工具调用参数正确性（使用 mock）
    - 测试错误处理和错误事件广播

- [ ] 7. Checkpoint - 验证后端 API
  - 使用 curl 或 Postman 测试所有 API 端点
  - 验证 WebSocket 事件正确推送
  - 验证文件系统操作正确性
  - 确保所有测试通过，询问用户是否继续

### Phase 4: 前端基础组件

- [ ] 8. 实现前端路由和导航
  - [ ] 8.1 添加文章路由配置
    - 在 `web/ui/src/router/index.ts` 中添加 `/articles` 路由
    - 添加 `/articles/:id` 路由
    - 配置路由懒加载
    - _Requirements: 12.1, 12.2_
  
  - [ ] 8.2 添加侧边栏导航菜单项
    - 在侧边栏组件中添加"文章"菜单项
    - 使用 📝 图标
    - 链接到 `/articles` 路由
    - _Requirements: 12.1, 12.3_

- [ ] 9. 实现 Markdown 编辑和预览组件
  - [ ] 9.1 创建 MarkdownEditor.vue 组件
    - 实现 textarea 或使用第三方编辑器库
    - 支持 v-model 双向绑定
    - 支持 placeholder 和 readonly 属性
    - _Requirements: 4.1, 4.3, 6.1, 6.3_
  
  - [ ] 9.2 创建 MarkdownPreview.vue 组件
    - 使用 marked 库渲染 Markdown 为 HTML
    - 使用 highlight.js 高亮代码块
    - 实时更新预览（watch content prop）
    - 添加样式美化渲染结果
    - _Requirements: 7.2, 7.3, 7.4_
  
  - [ ]* 9.3 编写 Markdown 组件单元测试
    - 测试编辑器输入和输出
    - 测试预览渲染正确性
    - 测试代码高亮功能

- [ ] 10. Checkpoint - 验证前端基础组件
  - 测试路由导航正常
  - 测试 Markdown 编辑器和预览功能
  - 确保所有测试通过，询问用户是否继续

### Phase 5: 前端页面实现

- [ ] 11. 实现文章列表页面
  - [ ] 11.1 创建 ArticleListPage.vue 组件
    - 实现页面布局（标题 + 新建按钮 + 列表）
    - 实现 `loadArticles()` 方法调用 GET /api/articles
    - 显示文章列表（标题、状态、时间）
    - 实现"新建文章"按钮，导航到编辑器
    - 实现"继续编辑"/"查看"按钮，导航到编辑器
    - 实现"删除"按钮，显示确认对话框
    - _Requirements: 9.1, 9.2, 9.4, 9.5, 9.6, 9.7, 10.1_
  
  - [ ]* 11.2 编写文章列表页面测试
    - 测试文章列表加载和显示
    - 测试新建文章按钮
    - 测试删除文章功能
    - 测试导航到编辑器

- [ ] 12. 实现文章编辑器页面
  - [ ] 12.1 创建 ArticleEditorPage.vue 基础结构
    - 实现页面布局（标题栏 + 内容区）
    - 实现 `loadArticle(id)` 方法加载文章数据
    - 实现状态管理（article, currentStep, loading, error）
    - 实现 WebSocket 连接管理（onMounted/onUnmounted）
    - _Requirements: 13.1, 13.2_
  
  - [ ] 12.2 实现标题输入步骤（step=title）
    - 显示标题输入框
    - 实现"保存标题"按钮调用 PUT /api/articles/{id}
    - 实现"生成骨架"按钮调用 POST /api/articles/{id}/outline
    - 显示加载状态和错误消息
    - _Requirements: 2.1, 3.6_
  
  - [ ] 12.3 实现骨架编辑步骤（step=outline）
    - 使用 MarkdownEditor 和 MarkdownPreview 组件
    - 实现左右分栏布局
    - 实现"保存草稿"按钮
    - 实现"重新生成"按钮
    - 实现"生成全文"按钮调用 POST /api/articles/{id}/generate
    - _Requirements: 4.2, 4.4, 4.5, 5.6, 7.5_
  
  - [ ] 12.4 实现内容编辑步骤（step=content）
    - 使用 MarkdownEditor 和 MarkdownPreview 组件
    - 实现"保存草稿"按钮
    - 实现"重新生成"按钮
    - 实现"预览"按钮切换到 preview 步骤
    - _Requirements: 6.2, 6.4, 6.6_
  
  - [ ] 12.5 实现预览步骤（step=preview）
    - 全屏显示 MarkdownPreview 组件
    - 实现"返回编辑"按钮
    - 实现"发布"按钮调用 POST /api/articles/{id}/publish
    - 发布成功后显示文章 URL
    - _Requirements: 8.1, 8.8_
  
  - [ ] 12.6 实现步骤导航
    - 实现"上一步"和"下一步"按钮
    - 根据 currentStep 显示对应界面
    - 更新 step 字段到后端
    - _Requirements: 13.3, 13.4, 13.5_
  
  - [ ] 12.7 实现 WebSocket 消息处理
    - 实现 `handleWebSocketMessage(event)` 方法
    - 处理 `article_outline_generated` 事件更新内容
    - 处理 `article_content_generated` 事件更新内容
    - 处理 `article_published` 事件显示成功消息
    - 处理 `article_error` 事件显示错误消息
    - 更新 loading 状态
    - _Requirements: Architecture requirement_
  
  - [ ]* 12.8 编写文章编辑器页面测试
    - 测试各步骤界面显示
    - 测试步骤导航
    - 测试 WebSocket 消息处理
    - 测试错误处理

- [ ] 13. Checkpoint - 验证前端页面
  - 手动测试完整工作流
  - 测试 WebSocket 实时更新
  - 测试错误处理和用户反馈
  - 确保所有测试通过，询问用户是否继续

### Phase 6: 集成测试和优化

- [ ] 14. 端到端集成测试
  - [ ]* 14.1 编写 E2E 测试（Playwright）
    - 测试完整工作流：创建 → 骨架 → 内容 → 发布
    - 测试 WebSocket 实时更新
    - 测试错误场景和恢复
    - 测试并发操作
  
  - [ ]* 14.2 编写 API 集成测试
    - 测试所有 API 端点
    - 测试 CLI 工具集成
    - 测试文件系统操作
    - 测试 WebSocket 事件

- [ ] 15. 错误处理和用户体验优化
  - [ ] 15.1 完善错误处理
    - 统一错误响应格式
    - 添加详细错误日志
    - 前端显示友好错误消息
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ] 15.2 优化加载状态和反馈
    - 添加加载动画
    - 优化 WebSocket 重连机制
    - 添加操作成功提示
    - 添加进度指示器
  
  - [ ] 15.3 优化性能
    - 实现文章列表分页（如果需要）
    - 优化 Markdown 渲染性能
    - 添加防抖和节流
    - 优化 WebSocket 消息频率

- [ ] 16. 文档和部署
  - [ ] 16.1 编写用户文档
    - 编写功能使用说明
    - 编写 API 文档
    - 编写故障排查指南
  
  - [ ] 16.2 编写开发者文档
    - 编写架构说明
    - 编写代码注释
    - 编写测试指南
  
  - [ ] 16.3 准备部署
    - 验证环境变量配置
    - 验证依赖安装
    - 验证文件权限
    - 编写部署脚本

- [ ] 17. Final Checkpoint - 完整验证
  - 运行所有测试套件
  - 手动测试所有功能
  - 验证性能和稳定性
  - 确认所有需求已实现

## 注意事项

1. **任务标记说明**：
   - 标记 `*` 的子任务为可选测试任务，可根据项目进度决定是否实施
   - 未标记 `*` 的任务为必须实现的核心功能

2. **实施顺序**：
   - 严格按照 Phase 顺序执行
   - 每个 Checkpoint 必须通过后才能继续下一阶段
   - 遇到问题及时与用户沟通

3. **CLI 工具集成**：
   - 所有 CLI 调用使用现有的 `_run_xpost()` 函数
   - 参考现有队列处理器的异步任务模式
   - 确保超时设置合理（init: 120s, generate: 300s, publish: 300s）

4. **WebSocket 最佳实践**：
   - 前端必须在 onUnmounted 时断开连接
   - 后端必须在 finally 块清理连接
   - 实现自动重连机制（指数退避）

5. **文件操作安全**：
   - 所有写操作使用原子性写入（临时文件 + 重命名）
   - 确保目录存在后再写入
   - 捕获并记录所有文件系统错误

6. **测试覆盖**：
   - 核心功能必须有单元测试
   - 关键工作流必须有集成测试
   - 可选测试任务可根据时间安排决定

## 技术栈

- **后端**: Python 3.11+, FastAPI, asyncio
- **前端**: Vue 3, TypeScript, Vite
- **实时通信**: WebSocket
- **Markdown**: marked, highlight.js
- **CLI 集成**: xpost.py (subprocess)
- **测试**: pytest, pytest-asyncio, Vitest, Playwright

## 预期交付物

1. 完整的后端 API（9 个端点）
2. WebSocket 实时通信系统
3. 前端文章列表页面
4. 前端文章编辑器页面
5. Markdown 编辑和预览组件
6. 完整的测试套件
7. 用户和开发者文档
