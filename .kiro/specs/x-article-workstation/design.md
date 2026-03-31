# 设计文档：X Article 创作工作站

## Overview

X Article 创作工作站是一个基于 Web 的长文创作系统，提供从选题到发布的完整工作流。系统采用前后端分离架构，通过 WebSocket 实现实时状态更新，集成现有的 `xpost.py` CLI 工具来处理文章生成和发布逻辑。

### 核心特性

- **工作流状态机**：title → outline → content → publish 四阶段流程
- **实时状态反馈**：通过 WebSocket 推送长时操作的进度更新
- **异步任务处理**：后台执行 CLI 工具调用，避免阻塞 API 响应
- **Markdown 编辑**：支持实时编辑和预览
- **数据持久化**：JSON 元数据 + Markdown 文件双重存储

### 技术栈

- **后端**：FastAPI (Python 3.11+)
- **前端**：Vue 3 + Vite + TypeScript
- **实时通信**：WebSocket
- **Markdown 渲染**：marked + highlight.js
- **CLI 集成**：xpost.py (subprocess)

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                        │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  ArticleList.vue │         │ ArticleEditor.vue│          │
│  │  - 文章列表       │         │  - 标题输入       │          │
│  │  - 新建/删除      │         │  - 骨架生成       │          │
│  └──────────────────┘         │  - 内容编辑       │          │
│                               │  - Markdown 预览  │          │
│                               └──────────────────┘          │
│                                       │                      │
│                                       │ WebSocket            │
│                                       ↓                      │
└───────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTP + WebSocket
                                        ↓
┌─────────────────────────────────────────────────────────────┐
│                      后端层 (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RESTful API 端点                         │   │
│  │  /api/articles (GET, POST)                           │   │
│  │  /api/articles/{id} (GET, PUT, DELETE)               │   │
│  │  /api/articles/{id}/outline (POST)                   │   │
│  │  /api/articles/{id}/generate (POST)                  │   │
│  │  /api/articles/{id}/publish (POST)                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           WebSocket 端点                              │   │
│  │  /ws/articles - 实时推送文章状态更新                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           异步任务处理器                              │   │
│  │  - 后台执行 CLI 工具调用                              │   │
│  │  - 通过 WebSocket 广播进度                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           CLI 工具集成层                              │   │
│  │  xpost init --topic "标题"                            │   │
│  │  xpost generate md_path                               │   │
│  │  xpost publish md_path --publish                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                        │
                                        ↓
┌─────────────────────────────────────────────────────────────┐
│                      存储层                                  │
│  xinfo/log/articles/                                         │
│  ├── {article_id}.json  (元数据)                             │
│  └── {article_id}.md    (Markdown 内容)                      │
└─────────────────────────────────────────────────────────────┘
```

### 架构设计决策

#### 1. 前后端分离

- **前端**：负责 UI 交互、状态管理、Markdown 编辑和预览
- **后端**：负责业务逻辑、CLI 工具调用、数据持久化
- **优势**：清晰的职责分离，便于独立开发和测试

#### 2. WebSocket 实时通信

参考 Post 发布队列的实现（commit 0a0042b），采用相同的 WebSocket 模式：

- **连接管理**：维护 `_ws_connections` 集合存储活跃连接
- **广播机制**：通过 `_broadcast_article_update()` 推送状态更新
- **事件类型**：
  - `article_outline_generating` - 骨架生成中
  - `article_outline_generated` - 骨架生成完成
  - `article_content_generating` - 内容生成中
  - `article_content_generated` - 内容生成完成
  - `article_publishing` - 发布中
  - `article_published` - 发布完成
  - `article_error` - 操作失败

#### 3. 异步任务处理

- **问题**：CLI 工具调用（init/generate/publish）可能耗时 30-300 秒
- **解决方案**：
  - API 端点立即返回 202 Accepted
  - 后台启动异步任务执行 CLI 工具
  - 通过 WebSocket 推送进度和结果
  - 前端监听 WebSocket 事件更新 UI

#### 4. 数据持久化策略

- **双重存储**：
  - JSON 文件：存储元数据（状态、时间戳、步骤等）
  - Markdown 文件：存储实际内容
- **原子写入**：先写临时文件，再重命名（避免数据损坏）
- **目录结构**：
  ```
  xinfo/log/articles/
  ├── art_1711781234567.json
  ├── art_1711781234567.md
  ├── art_1711781234568.json
  └── art_1711781234568.md
  ```

## Components and Interfaces

### 前端组件

#### 1. ArticleListPage.vue

**职责**：显示文章列表，提供新建和删除功能

**状态**：
```typescript
interface ArticleListState {
  articles: Article[]
  loading: boolean
  error: string | null
}
```

**方法**：
- `loadArticles()` - 加载文章列表
- `createArticle()` - 创建新文章
- `deleteArticle(id)` - 删除文章
- `navigateToEditor(id)` - 导航到编辑器

#### 2. ArticleEditorPage.vue

**职责**：文章编辑器，支持四阶段工作流

**状态**：
```typescript
interface ArticleEditorState {
  article: Article | null
  currentStep: 'title' | 'outline' | 'content' | 'preview'
  content: string
  loading: boolean
  error: string | null
  wsConnected: boolean
}
```

**方法**：
- `loadArticle(id)` - 加载文章数据
- `saveTitle(title)` - 保存标题
- `generateOutline()` - 生成骨架
- `generateContent()` - 生成全文
- `saveContent(content)` - 保存内容
- `publishArticle()` - 发布文章
- `connectWebSocket()` - 建立 WebSocket 连接
- `handleWebSocketMessage(event)` - 处理 WebSocket 消息

#### 3. MarkdownEditor.vue

**职责**：Markdown 文本编辑器组件

**Props**：
```typescript
interface MarkdownEditorProps {
  modelValue: string
  placeholder?: string
  readonly?: boolean
}
```

**Events**：
- `update:modelValue` - 内容变更

#### 4. MarkdownPreview.vue

**职责**：Markdown 实时预览组件

**Props**：
```typescript
interface MarkdownPreviewProps {
  content: string
}
```

**功能**：
- 使用 `marked` 渲染 Markdown 为 HTML
- 使用 `highlight.js` 高亮代码块
- 实时更新预览

### 后端 API 端点

#### 1. GET /api/articles

**功能**：获取文章列表

**响应**：
```json
{
  "ok": true,
  "articles": [
    {
      "id": "art_1711781234567",
      "title": "如何使用 AI 提升开发效率",
      "status": "draft",
      "step": "content",
      "created_at": "2026-03-30T10:00:00Z",
      "updated_at": "2026-03-30T11:30:00Z",
      "published_at": null
    }
  ]
}
```

#### 2. POST /api/articles

**功能**：创建新文章

**请求**：
```json
{
  "title": "如何使用 AI 提升开发效率"
}
```

**响应**：
```json
{
  "ok": true,
  "article_id": "art_1711781234567",
  "title": "如何使用 AI 提升开发效率"
}
```

#### 3. GET /api/articles/{id}

**功能**：获取文章详情

**响应**：
```json
{
  "ok": true,
  "article": {
    "id": "art_1711781234567",
    "title": "如何使用 AI 提升开发效率",
    "status": "draft",
    "step": "content",
    "content": "# 如何使用 AI 提升开发效率\n\n...",
    "created_at": "2026-03-30T10:00:00Z",
    "updated_at": "2026-03-30T11:30:00Z",
    "published_at": null,
    "md_path": "xinfo/log/articles/art_1711781234567.md"
  }
}
```

#### 4. PUT /api/articles/{id}

**功能**：更新文章内容

**请求**：
```json
{
  "content": "# 更新后的内容\n\n..."
}
```

**响应**：
```json
{
  "ok": true,
  "updated_at": "2026-03-30T12:00:00Z"
}
```

#### 5. DELETE /api/articles/{id}

**功能**：删除文章

**响应**：
```json
{
  "ok": true
}
```

#### 6. POST /api/articles/{id}/outline

**功能**：生成文章骨架（异步）

**响应**：
```json
{
  "ok": true,
  "status": "generating",
  "message": "骨架生成已启动，请通过 WebSocket 监听进度"
}
```

**WebSocket 事件**：
```json
{
  "type": "article_outline_generating",
  "article_id": "art_1711781234567",
  "timestamp": "2026-03-30T12:00:00Z"
}
```

```json
{
  "type": "article_outline_generated",
  "article_id": "art_1711781234567",
  "outline": "# 如何使用 AI 提升开发效率\n\n## 1. 引言\n...",
  "timestamp": "2026-03-30T12:00:30Z"
}
```

#### 7. POST /api/articles/{id}/generate

**功能**：生成文章全文（异步）

**响应**：
```json
{
  "ok": true,
  "status": "generating",
  "message": "内容生成已启动，请通过 WebSocket 监听进度"
}
```

**WebSocket 事件**：
```json
{
  "type": "article_content_generating",
  "article_id": "art_1711781234567",
  "timestamp": "2026-03-30T12:01:00Z"
}
```

```json
{
  "type": "article_content_generated",
  "article_id": "art_1711781234567",
  "content": "# 如何使用 AI 提升开发效率\n\n## 1. 引言\n\n在当今...",
  "timestamp": "2026-03-30T12:03:00Z"
}
```

#### 8. POST /api/articles/{id}/publish

**功能**：发布文章到 X 平台（异步）

**请求**：
```json
{
  "publish": true
}
```

**响应**：
```json
{
  "ok": true,
  "status": "publishing",
  "message": "发布已启动，请通过 WebSocket 监听进度"
}
```

**WebSocket 事件**：
```json
{
  "type": "article_publishing",
  "article_id": "art_1711781234567",
  "timestamp": "2026-03-30T12:05:00Z"
}
```

```json
{
  "type": "article_published",
  "article_id": "art_1711781234567",
  "article_url": "https://x.com/username/article/123",
  "timestamp": "2026-03-30T12:06:00Z"
}
```

#### 9. WebSocket /ws/articles

**功能**：实时推送文章状态更新

**连接流程**：
1. 客户端连接 `ws://localhost:8000/ws/articles`
2. 服务器发送初始状态（如果有正在进行的任务）
3. 服务器推送后续状态更新
4. 客户端监听消息并更新 UI

**消息格式**：
```json
{
  "type": "article_outline_generating" | "article_outline_generated" | 
         "article_content_generating" | "article_content_generated" |
         "article_publishing" | "article_published" | "article_error",
  "article_id": "art_1711781234567",
  "data": {},
  "timestamp": "2026-03-30T12:00:00Z"
}
```

### WebSocket 生命周期管理

#### 前端生命周期

**连接时机**：
- 用户进入文章编辑器页面（ArticleEditorPage）时建立连接
- 使用 Vue 的 `onMounted` 钩子

**断开时机**：
- 用户离开文章编辑器页面时断开连接
- 使用 Vue 的 `onUnmounted` 钩子
- 确保资源正确释放

**重连机制**：
- 连接意外断开时，3 秒后自动重连
- 使用指数退避策略，最大延迟 30 秒
- 重连前检查 `wsConnection` 是否为 null，避免重复连接

**实现示例**：
```typescript
// ArticleEditorPage.vue
let wsConnection: WebSocket | null = null
let reconnectDelay = 3000

function connectWebSocket() {
  // 防止重复连接
  if (wsConnection) return
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/articles`
  
  console.log('🔌 连接 WebSocket:', wsUrl)
  wsConnection = new WebSocket(wsUrl)
  
  wsConnection.onopen = () => {
    console.log('✅ WebSocket 已连接')
    reconnectDelay = 3000 // 重置重连延迟
  }
  
  wsConnection.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    } catch (e) {
      console.error('解析 WebSocket 消息失败:', e)
    }
  }
  
  wsConnection.onerror = (error) => {
    console.error('❌ WebSocket 错误:', error)
  }
  
  wsConnection.onclose = () => {
    console.log('🔌 WebSocket 已断开')
    wsConnection = null
    
    // 自动重连（仅在页面未卸载时）
    if (!isPageUnmounted.value) {
      setTimeout(() => {
        if (!wsConnection) {
          connectWebSocket()
        }
      }, reconnectDelay)
      
      // 指数退避，最大 30 秒
      reconnectDelay = Math.min(reconnectDelay * 2, 30000)
    }
  }
}

function disconnectWebSocket() {
  if (wsConnection) {
    console.log('🔌 主动断开 WebSocket')
    wsConnection.close()
    wsConnection = null
  }
}

const isPageUnmounted = ref(false)

onMounted(() => {
  isPageUnmounted.value = false
  connectWebSocket()
})

onUnmounted(() => {
  isPageUnmounted.value = true
  disconnectWebSocket()
})
```

#### 后端生命周期

**架构决策**：采用独立 WebSocket 端点（`/ws/articles`），与 Post 发布队列（`/ws/queue`）分离

**理由**：
- 职责清晰：Post 队列和 Article 工作站完全解耦
- 按需连接：用户只在相关页面建立连接，节省资源
- 独立扩展：互不影响，便于维护

**公共 WebSocket 管理器**：

为避免代码重复，抽取公共逻辑到 `WebSocketManager` 类：

```python
class WebSocketManager:
    """WebSocket 连接管理器 - 处理连接生命周期和消息广播"""
    
    def __init__(self, name: str):
        self.name = name
        self.connections: set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """接受并注册新连接"""
        await websocket.accept()
        self.connections.add(websocket)
        print(f"🔌 [{self.name}] WebSocket 连接建立，当前连接数: {len(self.connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开并清理连接"""
        self.connections.discard(websocket)
        print(f"🔌 [{self.name}] WebSocket 连接断开，当前连接数: {len(self.connections)}")
    
    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        if not self.connections:
            return
        
        disconnected = set()
        
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"⚠️  [{self.name}] 向 WebSocket 发送消息失败: {e}")
                disconnected.add(ws)
        
        # 清理断开的连接
        self.connections.difference_update(disconnected)
        
        if disconnected:
            print(f"🧹 [{self.name}] 清理了 {len(disconnected)} 个断开的连接")
    
    async def close_all(self):
        """关闭所有连接（应用关闭时调用）"""
        print(f"🧹 [{self.name}] 关闭 {len(self.connections)} 个 WebSocket 连接")
        
        for ws in list(self.connections):
            try:
                await ws.close()
            except Exception:
                pass
        
        self.connections.clear()


# 创建管理器实例
_queue_ws_manager = WebSocketManager("Queue")
_article_ws_manager = WebSocketManager("Article")
```

**Article WebSocket 端点实现**：

```python
@app.websocket("/ws/articles")
async def websocket_articles(websocket: WebSocket):
    """WebSocket 端点 - 实时推送文章状态更新"""
    await _article_ws_manager.connect(websocket)
    
    try:
        # 保持连接，等待客户端断开
        while True:
            try:
                # 接收客户端消息（心跳或命令）
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"⚠️  [Article] WebSocket 错误: {e}")
    finally:
        _article_ws_manager.disconnect(websocket)


async def _broadcast_article_update(event_type: str, article_id: str, data: dict = None):
    """广播文章更新到所有 Article WebSocket 连接"""
    message = {
        "type": event_type,
        "article_id": article_id,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await _article_ws_manager.broadcast(message)
```

**重构现有 Queue WebSocket**：

```python
@app.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    """WebSocket 端点 - 实时推送队列更新"""
    await _queue_ws_manager.connect(websocket)
    
    try:
        # 发送当前队列状态
        data = _read_publish_queue()
        await websocket.send_json({
            "type": "initial",
            "queue": data.get("queue", [])
        })
        
        # 保持连接，等待客户端断开
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"⚠️  [Queue] WebSocket 错误: {e}")
    finally:
        _queue_ws_manager.disconnect(websocket)


async def _broadcast_queue_update(event_type: str, task_id: str = None, task: dict = None):
    """广播队列更新到所有 Queue WebSocket 连接"""
    message = {
        "type": event_type,
        "task_id": task_id,
        "task": task,
        "timestamp": datetime.now().isoformat()
    }
    
    await _queue_ws_manager.broadcast(message)
```

#### 应用启动和关闭

**启动时**：
- 初始化 WebSocket 管理器实例
- 无需额外操作

**关闭时**：
- FastAPI 的 `@app.on_event("shutdown")` 钩子中关闭所有连接
- 确保没有悬挂的连接

```python
@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理所有 WebSocket 连接"""
    await _queue_ws_manager.close_all()
    await _article_ws_manager.close_all()
```

#### WebSocket 端点对比

| 特性 | `/ws/queue` | `/ws/articles` |
|------|-------------|----------------|
| **用途** | Post 发布队列状态更新 | Article 工作站实时反馈 |
| **连接时机** | 用户进入 PublishPage | 用户进入 ArticleEditorPage |
| **消息类型** | task_added, task_completed, task_failed | article_outline_generating, article_content_generated, etc. |
| **生命周期** | 页面级（onMounted/onUnmounted） | 页面级（onMounted/onUnmounted） |
| **管理器** | `_queue_ws_manager` | `_article_ws_manager` |
| **初始消息** | 发送当前队列状态 | 无（按需推送） |

#### 生命周期总结

| 阶段 | 前端 | 后端 |
|------|------|------|
| **连接建立** | `onMounted` 时调用 `connectWebSocket()` | `websocket.accept()` 并添加到 `_ws_connections` |
| **连接保持** | 监听 `onmessage` 事件 | `while True: await receive_text()` |
| **正常断开** | `onUnmounted` 时调用 `disconnectWebSocket()` | 捕获 `WebSocketDisconnect` |
| **异常断开** | `onclose` 触发，3 秒后重连 | 捕获异常，`finally` 清理连接 |
| **资源清理** | 设置 `wsConnection = null` | `_ws_connections.discard(websocket)` |
| **应用关闭** | 浏览器自动断开 | `shutdown_event` 关闭所有连接 |

#### 最佳实践

1. **防止内存泄漏**：
   - 前端：`onUnmounted` 必须调用 `disconnectWebSocket()`
   - 后端：`finally` 块必须清理连接

2. **防止重复连接**：
   - 前端：`connectWebSocket()` 开头检查 `if (wsConnection) return`
   - 后端：每个客户端只维护一个连接

3. **优雅降级**：
   - WebSocket 连接失败时，前端回退到轮询 API
   - 不影响核心功能使用

4. **日志记录**：
   - 连接建立/断开时打印日志
   - 记录当前连接数，便于监控

5. **错误处理**：
   - 捕获所有异常，避免崩溃
   - 广播失败时自动清理断开的连接

### CLI 工具集成接口

#### 1. xpost init

**调用方式**：
```python
await _run_xpost("init", md_path, "--topic", title)
```

**返回**：
```json
{
  "created": true,
  "md_path": "/path/to/article.md",
  "images_dir": "/path/to/images",
  "style": null,
  "topic": "如何使用 AI 提升开发效率",
  "prompt_included": true
}
```

#### 2. xpost generate

**调用方式**：
```python
await _run_xpost("generate", md_path)
```

**返回**：
```json
{
  "ok": true,
  "output_path": "/path/to/article.md",
  "backup_path": "/path/to/article.md.backup_20260330_120000",
  "elapsed_seconds": 120.5
}
```

#### 3. xpost publish

**调用方式**：
```python
await _run_xpost("publish", md_path, "--publish")
```

**返回**：
```json
{
  "ok": true,
  "mode": "publish",
  "article_url": "https://x.com/username/article/123"
}
```

## Data Models

### Article 数据模型

**JSON 文件**：`xinfo/log/articles/{article_id}.json`

```typescript
interface Article {
  id: string                    // 格式：art_<timestamp>
  title: string                 // 文章标题
  status: 'draft' | 'published' // 文章状态
  step: 'title' | 'outline' | 'content' | 'preview' // 当前步骤
  content: string               // Markdown 内容
  created_at: string            // ISO 8601 格式
  updated_at: string            // ISO 8601 格式
  published_at: string | null   // ISO 8601 格式
  md_path: string               // Markdown 文件路径
  publish_result: PublishResult | null // 发布结果
}

interface PublishResult {
  article_url: string           // X 平台文章 URL
  published_at: string          // 发布时间
}
```

**示例**：
```json
{
  "id": "art_1711781234567",
  "title": "如何使用 AI 提升开发效率",
  "status": "draft",
  "step": "content",
  "content": "# 如何使用 AI 提升开发效率\n\n## 1. 引言\n\n在当今快速发展的技术环境中...",
  "created_at": "2026-03-30T10:00:00Z",
  "updated_at": "2026-03-30T11:30:00Z",
  "published_at": null,
  "md_path": "xinfo/log/articles/art_1711781234567.md",
  "publish_result": null
}
```

### WebSocket 消息模型

```typescript
interface WebSocketMessage {
  type: ArticleEventType
  article_id: string
  data?: any
  error?: string
  timestamp: string
}

type ArticleEventType =
  | 'article_outline_generating'
  | 'article_outline_generated'
  | 'article_content_generating'
  | 'article_content_generated'
  | 'article_publishing'
  | 'article_published'
  | 'article_error'
```

### 工作流状态机

```
┌─────────┐
│  title  │ ─── 用户输入标题 ───→ 创建文章记录
└─────────┘
     │
     │ 点击"生成骨架"
     ↓
┌─────────┐
│ outline │ ─── CLI: xpost init ───→ 生成骨架 Markdown
└─────────┘
     │
     │ 用户编辑骨架（可选）
     │ 点击"生成全文"
     ↓
┌─────────┐
│ content │ ─── CLI: xpost generate ───→ 生成完整内容
└─────────┘
     │
     │ 用户编辑内容（可选）
     │ 点击"预览"
     ↓
┌─────────┐
│ preview │ ─── Markdown 渲染预览
└─────────┘
     │
     │ 点击"发布"
     ↓
┌───────────┐
│ published │ ─── CLI: xpost publish ───→ 发布到 X 平台
└───────────┘
```

**状态转换规则**：
- `title` → `outline`：调用 `POST /api/articles/{id}/outline`
- `outline` → `content`：调用 `POST /api/articles/{id}/generate`
- `content` → `preview`：前端本地渲染，无需 API 调用
- `preview` → `published`：调用 `POST /api/articles/{id}/publish`
- 任何步骤都可以通过 `PUT /api/articles/{id}` 保存草稿

### 文件系统布局

```
xinfo/log/articles/
├── art_1711781234567.json      # 文章元数据
├── art_1711781234567.md        # 文章 Markdown 内容
├── art_1711781234568.json
├── art_1711781234568.md
└── images/                     # 共享图片目录（可选）
    ├── cover.png
    └── demo1.png
```

**文件命名规则**：
- 文章 ID 格式：`art_<timestamp_ms>`
- JSON 文件：`{article_id}.json`
- Markdown 文件：`{article_id}.md`


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas of redundancy:

1. **CLI Parameter Passing**: Requirements 3.2, 5.2, 8.3, 16.2, 16.3, 16.4 all test CLI parameter passing. These can be consolidated into comprehensive properties for each CLI command.

2. **Error Handling**: Requirements 3.7, 5.7, 8.7, 14.4, 16.7 all test CLI error handling. These can be combined into a single property about error propagation.

3. **File Operations**: Requirements 1.5, 3.4, 5.4, 10.2, 10.3, 15.1, 15.2 test file persistence. These can be consolidated into properties about data persistence round-trips.

4. **Status Updates**: Requirements 1.4, 3.5, 5.5, 8.4, 13.1 test status field updates. These can be combined into properties about state transitions.

5. **API Response Format**: Requirements 11.9, 11.10, 14.2 test response format. These can be combined into a single property about API response structure.

The following properties eliminate redundancy while maintaining comprehensive coverage.

### Property 1: Article ID Format and Uniqueness

*For any* article creation request, the generated article ID should match the format `art_<timestamp>` and be unique across all articles in the system.

**Validates: Requirements 1.2**

### Property 2: Article Status Lifecycle

*For any* article, the status field should only contain valid values ('draft' or 'published'), and transitions should follow the rule: draft → published (one-way, no reverse).

**Validates: Requirements 1.1, 8.4**

### Property 3: Timestamp Management

*For any* article operation (create, update, publish), the system should maintain correct timestamps: created_at is set on creation and never changes, updated_at changes on any modification, and published_at is set only when status becomes 'published'.

**Validates: Requirements 1.3, 1.4, 8.5**

### Property 4: Data Persistence Round-Trip

*For any* article, after saving to disk (JSON + Markdown files), reading back the data should produce an equivalent article object with the same id, title, status, step, content, and timestamps.

**Validates: Requirements 1.5, 3.4, 5.4, 6.5, 15.1, 15.2, 15.5**

### Property 5: Title Validation

*For any* article creation request, if the title is empty or contains only whitespace, the API should reject the request with an error response.

**Validates: Requirements 2.2, 2.3**

### Property 6: Valid Title Creates Article

*For any* non-empty title string, submitting it to the article creation endpoint should successfully create a new article with step='title' and status='draft'.

**Validates: Requirements 2.4, 2.5**

### Property 7: Outline Generation Workflow

*For any* article in 'title' step, requesting outline generation should invoke `xpost init` with the correct parameters (md_path and --topic), and upon success, update the article's step to 'outline' and save the generated content to both JSON and Markdown files.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 16.2**

### Property 8: Content Generation Workflow

*For any* article in 'outline' step, requesting content generation should invoke `xpost generate` with the correct md_path parameter, and upon success, update the article's step to 'content' and save the generated content to both JSON and Markdown files.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 16.3**

### Property 9: Publish Workflow

*For any* article in 'content' or 'preview' step, requesting publication should invoke `xpost publish` with --publish flag, and upon success, update the article's status to 'published', set published_at timestamp, and save the article URL in publish_result.

**Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 16.4**

### Property 10: CLI Error Propagation

*For any* CLI command invocation (init, generate, publish), if the CLI tool returns a non-zero exit code, the API should return an error response with ok=false and include the error message from the CLI tool.

**Validates: Requirements 3.7, 5.7, 8.7, 14.4, 16.6, 16.7**

### Property 11: Article List Ordering

*For any* set of articles, the GET /api/articles endpoint should return them sorted by updated_at in descending order (most recently updated first).

**Validates: Requirements 9.3**

### Property 12: Article Deletion Completeness

*For any* existing article, deleting it should remove both the JSON metadata file and the Markdown content file from the filesystem, and subsequent GET requests for that article should return 404.

**Validates: Requirements 10.2, 10.3**

### Property 13: Step Transition Validity

*For any* article, the step field should only contain valid values ('title', 'outline', 'content', 'preview'), and step transitions should follow the workflow: title → outline → content → preview, with the ability to move backward but not skip steps.

**Validates: Requirements 13.1, 13.4, 13.5**

### Property 14: API Response Structure

*For any* API endpoint response, it should be valid JSON containing an 'ok' boolean field, and if ok=false, it should also contain an 'error' field with a descriptive message.

**Validates: Requirements 11.9, 11.10, 14.2**

### Property 15: HTTP Status Code Correctness

*For any* API request, the response HTTP status code should match the operation result: 2xx for success, 4xx for client errors (invalid input, not found), and 5xx for server errors (CLI failure, file system errors).

**Validates: Requirements 14.1**

### Property 16: Atomic File Writes

*For any* file write operation, if the process is interrupted mid-write, the original file should remain intact (no partial writes or corruption).

**Validates: Requirements 15.3**

### Property 17: Directory Auto-Creation

*For any* article save operation, if the storage directory (xinfo/log/articles/) does not exist, the system should automatically create it before writing files.

**Validates: Requirements 15.4**

### Property 18: WebSocket Event Consistency

*For any* long-running operation (outline generation, content generation, publishing), the system should broadcast WebSocket events in the correct sequence: *_generating → *_generated (or *_error), and the article_id in the event should match the article being processed.

**Validates: Architecture requirement for real-time updates**

## Error Handling

### Error Categories

#### 1. Client Errors (4xx)

**400 Bad Request**
- Empty or whitespace-only title
- Invalid step transition request
- Missing required parameters
- Invalid article ID format

**404 Not Found**
- Article ID does not exist
- Markdown file not found

**409 Conflict**
- Attempting to publish an already published article
- Concurrent modification conflicts

#### 2. Server Errors (5xx)

**500 Internal Server Error**
- CLI tool execution failure
- File system I/O errors
- JSON parsing errors
- Unexpected exceptions

**503 Service Unavailable**
- CLI tool timeout (>600 seconds)
- System resource exhaustion

### Error Response Format

All error responses follow this structure:

```json
{
  "ok": false,
  "error": "Descriptive error message",
  "error_code": "ERROR_CODE",
  "details": {
    // Optional additional context
  }
}
```

### Error Handling Strategies

#### 1. CLI Tool Failures

**Strategy**: Capture stdout, stderr, and exit code

```python
async def _run_xpost_safe(*args):
    try:
        result = await _run_xpost(*args, timeout=600)
        if result.get("ok") is False:
            return {
                "ok": False,
                "error": result.get("error", "CLI tool failed"),
                "cli_output": result
            }
        return result
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "CLI tool execution timeout (>600s)",
            "error_code": "CLI_TIMEOUT"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"CLI tool execution failed: {str(e)}",
            "error_code": "CLI_ERROR"
        }
```

#### 2. File System Errors

**Strategy**: Atomic writes with rollback

```python
async def _save_article_atomic(article_id: str, data: dict):
    json_path = ARTICLES_DIR / f"{article_id}.json"
    temp_path = json_path.with_suffix(".json.tmp")
    
    try:
        # Write to temporary file
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        # Atomic rename
        temp_path.rename(json_path)
        return {"ok": True}
    except Exception as e:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
        return {
            "ok": False,
            "error": f"Failed to save article: {str(e)}",
            "error_code": "FILE_WRITE_ERROR"
        }
```

#### 3. WebSocket Connection Errors

**Strategy**: Graceful degradation

- If WebSocket connection fails, operations continue but without real-time updates
- Frontend polls API for status updates as fallback
- Automatic reconnection with exponential backoff

```typescript
function connectWebSocket() {
  const ws = new WebSocket('ws://localhost:8000/ws/articles')
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    // Fall back to polling
    startPolling()
  }
  
  ws.onclose = () => {
    // Reconnect with exponential backoff
    setTimeout(() => connectWebSocket(), reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, 30000)
  }
}
```

#### 4. Concurrent Modification

**Strategy**: Optimistic locking with updated_at timestamp

```python
async def update_article(article_id: str, content: str, expected_updated_at: str):
    article = _read_article(article_id)
    
    if article["updated_at"] != expected_updated_at:
        return {
            "ok": False,
            "error": "Article was modified by another process",
            "error_code": "CONCURRENT_MODIFICATION",
            "current_updated_at": article["updated_at"]
        }
    
    # Proceed with update
    article["content"] = content
    article["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_article(article_id, article)
    
    return {"ok": True, "updated_at": article["updated_at"]}
```

### Error Logging

All errors are logged with structured context:

```python
import logging

logger = logging.getLogger("article_workstation")

async def generate_outline(article_id: str):
    try:
        # ... operation
    except Exception as e:
        logger.error(
            "Outline generation failed",
            extra={
                "article_id": article_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        raise
```

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and integration points
- **Property tests**: Verify universal properties across randomized inputs

### Unit Testing

**Focus Areas**:
- API endpoint integration (request/response handling)
- WebSocket connection management
- File system operations (create, read, update, delete)
- CLI tool integration (mocking subprocess calls)
- Error handling for specific scenarios

**Example Unit Tests**:

```python
# Test: Empty title rejection
async def test_create_article_empty_title():
    response = await client.post("/api/articles", json={"title": ""})
    assert response.status_code == 400
    assert response.json()["ok"] is False
    assert "error" in response.json()

# Test: Article creation success
async def test_create_article_success():
    response = await client.post("/api/articles", json={"title": "Test Article"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["article_id"].startswith("art_")
    assert data["title"] == "Test Article"

# Test: WebSocket connection
async def test_websocket_connection():
    async with client.websocket_connect("/ws/articles") as ws:
        # Should receive initial message
        data = await ws.receive_json()
        assert "type" in data
```

### Property-Based Testing

**Library**: Use `hypothesis` for Python property-based testing

**Configuration**: Minimum 100 iterations per property test

**Property Test Examples**:

```python
from hypothesis import given, strategies as st

# Property 1: Article ID Format and Uniqueness
@given(st.text(min_size=1, max_size=200))
async def test_property_article_id_format(title: str):
    """
    Feature: x-article-workstation, Property 1: 
    For any article creation request, the generated article ID 
    should match the format art_<timestamp> and be unique.
    """
    response = await client.post("/api/articles", json={"title": title})
    if response.status_code == 200:
        article_id = response.json()["article_id"]
        assert re.match(r"^art_\d+$", article_id)
        # Verify uniqueness by checking it doesn't exist yet
        # (in practice, check against existing IDs)

# Property 4: Data Persistence Round-Trip
@given(
    st.text(min_size=1, max_size=200),
    st.text(min_size=0, max_size=10000)
)
async def test_property_persistence_round_trip(title: str, content: str):
    """
    Feature: x-article-workstation, Property 4:
    For any article, after saving to disk, reading back 
    should produce equivalent data.
    """
    # Create article
    create_resp = await client.post("/api/articles", json={"title": title})
    article_id = create_resp.json()["article_id"]
    
    # Update content
    await client.put(f"/api/articles/{article_id}", json={"content": content})
    
    # Read back
    get_resp = await client.get(f"/api/articles/{article_id}")
    article = get_resp.json()["article"]
    
    # Verify round-trip
    assert article["id"] == article_id
    assert article["title"] == title
    assert article["content"] == content
    assert article["status"] == "draft"

# Property 11: Article List Ordering
@given(st.lists(st.text(min_size=1, max_size=100), min_size=2, max_size=10))
async def test_property_list_ordering(titles: list[str]):
    """
    Feature: x-article-workstation, Property 11:
    For any set of articles, GET /api/articles should return 
    them sorted by updated_at descending.
    """
    # Create articles with delays to ensure different timestamps
    article_ids = []
    for title in titles:
        resp = await client.post("/api/articles", json={"title": title})
        article_ids.append(resp.json()["article_id"])
        await asyncio.sleep(0.01)  # Ensure different timestamps
    
    # Update articles in random order
    import random
    random.shuffle(article_ids)
    for article_id in article_ids:
        await client.put(f"/api/articles/{article_id}", json={"content": "updated"})
        await asyncio.sleep(0.01)
    
    # Get list
    resp = await client.get("/api/articles")
    articles = resp.json()["articles"]
    
    # Verify ordering
    timestamps = [a["updated_at"] for a in articles]
    assert timestamps == sorted(timestamps, reverse=True)

# Property 14: API Response Structure
@given(st.sampled_from([
    ("GET", "/api/articles"),
    ("POST", "/api/articles", {"title": "Test"}),
    ("GET", "/api/articles/art_123"),
    ("DELETE", "/api/articles/art_123"),
]))
async def test_property_api_response_structure(endpoint_data):
    """
    Feature: x-article-workstation, Property 14:
    For any API endpoint, response should be valid JSON 
    with 'ok' field, and 'error' field if ok=false.
    """
    method, path, *body = endpoint_data
    if method == "GET":
        resp = await client.get(path)
    elif method == "POST":
        resp = await client.post(path, json=body[0] if body else {})
    elif method == "DELETE":
        resp = await client.delete(path)
    
    data = resp.json()
    assert "ok" in data
    assert isinstance(data["ok"], bool)
    
    if not data["ok"]:
        assert "error" in data
        assert isinstance(data["error"], str)
```

### Integration Testing

**Focus**: End-to-end workflows

```python
async def test_full_article_workflow():
    """Test complete workflow: create → outline → content → publish"""
    
    # 1. Create article
    resp = await client.post("/api/articles", json={"title": "Test Article"})
    article_id = resp.json()["article_id"]
    
    # 2. Generate outline (mock CLI)
    with mock.patch("server._run_xpost") as mock_xpost:
        mock_xpost.return_value = {
            "ok": True,
            "created": True,
            "md_path": f"xinfo/log/articles/{article_id}.md"
        }
        resp = await client.post(f"/api/articles/{article_id}/outline")
        assert resp.json()["ok"] is True
    
    # 3. Generate content (mock CLI)
    with mock.patch("server._run_xpost") as mock_xpost:
        mock_xpost.return_value = {
            "ok": True,
            "output_path": f"xinfo/log/articles/{article_id}.md"
        }
        resp = await client.post(f"/api/articles/{article_id}/generate")
        assert resp.json()["ok"] is True
    
    # 4. Publish (mock CLI)
    with mock.patch("server._run_xpost") as mock_xpost:
        mock_xpost.return_value = {
            "ok": True,
            "mode": "publish",
            "article_url": "https://x.com/user/article/123"
        }
        resp = await client.post(f"/api/articles/{article_id}/publish", json={"publish": True})
        assert resp.json()["ok"] is True
    
    # 5. Verify final state
    resp = await client.get(f"/api/articles/{article_id}")
    article = resp.json()["article"]
    assert article["status"] == "published"
    assert article["published_at"] is not None
    assert article["publish_result"]["article_url"] == "https://x.com/user/article/123"
```

### Frontend Testing

**Unit Tests** (Vitest):
- Component rendering
- User interactions (button clicks, form submissions)
- WebSocket message handling
- Markdown preview rendering

**E2E Tests** (Playwright):
- Complete user workflows
- Real WebSocket connections
- Browser compatibility

```typescript
// Example: Vitest component test
import { mount } from '@vue/test-utils'
import ArticleEditor from '@/views/ArticleEditor.vue'

test('ArticleEditor displays title input', () => {
  const wrapper = mount(ArticleEditor)
  expect(wrapper.find('input[type="text"]').exists()).toBe(true)
})

// Example: Playwright E2E test
test('create and publish article', async ({ page }) => {
  await page.goto('http://localhost:5173/articles')
  await page.click('text=新建文章')
  await page.fill('input[placeholder="输入文章标题"]', 'Test Article')
  await page.click('text=生成骨架')
  // Wait for WebSocket update
  await page.waitForSelector('text=骨架生成完成')
  await page.click('text=生成全文')
  await page.waitForSelector('text=内容生成完成')
  await page.click('text=发布')
  await page.waitForSelector('text=发布成功')
})
```

### Test Coverage Goals

- **Backend**: >80% line coverage, 100% of critical paths
- **Frontend**: >70% component coverage
- **Property tests**: All 18 properties implemented
- **Integration tests**: All major workflows covered

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio hypothesis
      - name: Run unit tests
        run: pytest tests/unit -v
      - name: Run property tests
        run: pytest tests/properties -v --hypothesis-seed=random
      - name: Run integration tests
        run: pytest tests/integration -v
      - name: Frontend tests
        run: |
          cd web/ui
          npm install
          npm run test
```

---

## Summary

This design document specifies a complete X Article creation workstation with:

1. **Architecture**: Front-end/back-end separation with WebSocket real-time communication
2. **Components**: Vue 3 frontend, FastAPI backend, CLI tool integration
3. **Data Models**: JSON metadata + Markdown content dual storage
4. **Workflows**: Four-stage state machine (title → outline → content → publish)
5. **Error Handling**: Comprehensive strategies for CLI, file system, and network errors
6. **Testing**: Dual approach with unit tests and property-based tests (18 properties)

The system leverages existing infrastructure (WebSocket patterns from Post publishing) and integrates seamlessly with the xpost.py CLI tool for article generation and publishing.
