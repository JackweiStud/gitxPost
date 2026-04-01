# X Article 工作站用户体验优化 - 设计文档

## Overview

This design addresses critical UX issues in the current article workflow by introducing a streamlined one-click generation system, optimized layout, enhanced real-time feedback, and improved editing experience. The solution maintains backward compatibility with existing APIs while adding new workflow orchestration capabilities.

### Current Pain Points

1. **Fragmented Workflow**: Users must manually trigger each step (outline → content → publish) with waiting periods between each action
2. **Poor Feedback**: Limited progress visibility during generation, unclear status indicators
3. **Inefficient Layout**: 50/50 split-screen wastes space, step indicators consume vertical real estate
4. **Missing Features**: No auto-save, no keyboard shortcuts, no undo/redo

### Design Goals

1. **Workflow Simplification**: One-click generation that auto-completes outline → content flow
2. **Enhanced Feedback**: Real-time progress indicators, clear status messages, obvious error handling
3. **Layout Optimization**: Compact interface with larger editing space, collapsible preview
4. **Efficiency Improvements**: Auto-save, keyboard shortcuts, smart suggestions

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Vue Frontend (UI)                        │
├─────────────────────────────────────────────────────────────┤
│  ArticleEditorPage.vue (Enhanced)                           │
│  ├─ WorkflowOrchestrator (New Component)                    │
│  ├─ CompactHeader (New Component)                           │
│  ├─ FloatingActionPanel (New Component)                     │
│  ├─ ProgressIndicator (New Component)                       │
│  ├─ MarkdownEditor (Enhanced with auto-save)                │
│  └─ MarkdownPreview (Collapsible)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket + REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (server.py)                 │
├─────────────────────────────────────────────────────────────┤
│  Existing Endpoints:                                         │
│  ├─ POST /api/articles/{id}/outline                         │
│  ├─ POST /api/articles/{id}/generate                        │
│  ├─ POST /api/articles/{id}/publish                         │
│  └─ PUT /api/articles/{id}                                  │
│                                                              │
│  New Endpoints:                                              │
│  ├─ POST /api/articles/{id}/auto-generate (New)             │
│  └─ POST /api/articles/{id}/cancel (New)                    │
│                                                              │
│  WebSocket Events (Enhanced):                                │
│  ├─ article_outline_generating                              │
│  ├─ article_outline_progress (New)                          │
│  ├─ article_outline_generated                               │
│  ├─ article_content_generating                              │
│  ├─ article_content_progress (New)                          │
│  ├─ article_content_generated                               │
│  └─ article_error                                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ subprocess calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    xpost CLI (Python)                        │
│  ├─ xpost init (outline generation)                         │
│  ├─ xpost generate (content generation)                     │
│  └─ xpost publish (article publishing)                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

#### One-Click Generation Flow

```
User clicks "一键生成"
    │
    ├─> Frontend: WorkflowOrchestrator.startAutoGeneration()
    │       │
    │       ├─> POST /api/articles/{id}/auto-generate
    │       │
    │       └─> WebSocket: Listen for progress events
    │
    ├─> Backend: auto_generate_article()
    │       │
    │       ├─> Step 1: Generate Outline
    │       │     ├─> Broadcast: article_outline_generating
    │       │     ├─> Call: xpost init
    │       │     ├─> Broadcast: article_outline_progress (0-100%)
    │       │     └─> Broadcast: article_outline_generated
    │       │
    │       ├─> Step 2: Generate Content
    │       │     ├─> Broadcast: article_content_generating
    │       │     ├─> Call: xpost generate
    │       │     ├─> Broadcast: article_content_progress (0-100%)
    │       │     └─> Broadcast: article_content_generated
    │       │
    │       └─> Return: {ok: true, completed_steps: ["outline", "content"]}
    │
    └─> Frontend: Update UI with generated content
```

#### Auto-Save Flow

```
User edits content
    │
    ├─> Debounce 3 seconds
    │
    ├─> PUT /api/articles/{id}
    │       │
    │       └─> Update article.updated_at
    │
    └─> Show "已自动保存 于 HH:MM"
```

## Components and Interfaces

### Frontend Components

#### 1. WorkflowOrchestrator (New)

Manages the one-click generation workflow and state transitions.

```typescript
interface WorkflowOrchestrator {
  // State
  currentStep: 'idle' | 'outline' | 'content' | 'complete' | 'error'
  progress: number  // 0-100
  canCancel: boolean
  
  // Methods
  startAutoGeneration(): Promise<void>
  cancelGeneration(): Promise<void>
  retryFromStep(step: string): Promise<void>
  
  // Events
  onStepChange(callback: (step: string) => void): void
  onProgressUpdate(callback: (progress: number) => void): void
  onError(callback: (error: string) => void): void
}
```

#### 2. CompactHeader (New)

Replaces the bulky header with a streamlined version including style selector.

```vue
<template>
  <div class="compact-header">
    <button class="btn-back" @click="goBack">← 返回</button>
    <input 
      v-model="title" 
      class="title-input" 
      @blur="saveTitle"
      placeholder="文章标题"
    />
    <select v-model="style" class="style-selector" @change="onStyleChange">
      <option value="zara">Zara 风格</option>
      <option value="tech">技术风格</option>
      <option value="fun">趣味风格</option>
    </select>
    <div class="header-actions">
      <span class="step-badge">{{ currentStepLabel }}</span>
      <span class="status-badge" :class="statusClass">{{ statusLabel }}</span>
    </div>
  </div>
</template>
```

**Height**: ~60px (vs current ~120px)

**Style Selector**:
- Dropdown with 3 options: zara, tech, fun
- Disabled during generation
- Saved to article metadata
- Remembered for next article (localStorage)

#### 3. FloatingActionPanel (New)

Fixed bottom-right panel with primary actions.

```vue
<template>
  <div class="floating-panel">
    <div class="save-status">{{ saveStatus }}</div>
    <button 
      v-if="canGenerate" 
      class="btn-primary btn-large"
      @click="startGeneration"
      :disabled="generating"
    >
      {{ generating ? '生成中...' : '一键生成' }}
    </button>
    <button 
      v-if="canPublish" 
      class="btn-success btn-large"
      @click="publish"
    >
      发布文章
    </button>
    <button class="btn-icon" @click="togglePreview">
      <PreviewIcon />
    </button>
  </div>
</template>
```

#### 4. ProgressIndicator (New)

Shows detailed progress during generation.

```vue
<template>
  <div v-if="visible" class="progress-indicator">
    <div class="progress-header">
      <span class="progress-title">{{ currentStepTitle }}</span>
      <span class="progress-percent">{{ progress }}%</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }"></div>
    </div>
    <div class="progress-message">{{ statusMessage }}</div>
    <button v-if="canCancel" class="btn-cancel" @click="cancel">
      取消
    </button>
  </div>
</template>
```

**Progress Messages**:
- Outline: "正在分析主题..." (0-30%) → "正在生成大纲..." (30-70%) → "正在优化结构..." (70-100%)
- Content: "正在扩展第 1/5 章节..." → "正在扩展第 2/5 章节..." etc.

#### 5. Enhanced MarkdownEditor

Adds auto-save, keyboard shortcuts, undo/redo, and image insertion.

```typescript
interface EnhancedMarkdownEditor {
  // Auto-save
  autoSaveDelay: number  // 3000ms
  lastSaved: Date | null
  saveStatus: 'saved' | 'saving' | 'unsaved' | 'error'
  
  // Keyboard shortcuts
  shortcuts: {
    'Cmd+S': () => void  // Manual save
    'Cmd+Z': () => void  // Undo
    'Cmd+Shift+Z': () => void  // Redo
    'Cmd+P': () => void  // Toggle preview
    'Cmd+V': (e: ClipboardEvent) => void  // Paste image
  }
  
  // History
  undoStack: string[]
  redoStack: string[]
  maxHistorySize: number  // 50
  
  // Image insertion
  insertImage(file: File): Promise<void>
  onDrop(e: DragEvent): void
  onPaste(e: ClipboardEvent): void
  uploadImage(file: File): Promise<string>  // Returns markdown syntax
}
```

**Image Insertion Features**:
- Drag & drop images onto editor
- Click toolbar button to select image file
- Paste image from clipboard (Cmd/Ctrl+V)
- Show upload progress indicator
- Auto-insert markdown syntax after upload
- Support common formats: PNG, JPG, GIF, WebP

### Backend API Endpoints

#### New Endpoint: Auto-Generate

```python
@app.post("/api/articles/{article_id}/auto-generate")
async def auto_generate_article(article_id: str, style: str = "zara"):
    """
    一键生成：自动完成 outline → content 流程
    
    Args:
        article_id: 文章 ID
        style: 文章风格 (zara/tech/fun)
    
    Returns:
        {
            "ok": true,
            "article_id": "art_123",
            "status": "generating",
            "message": "自动生成任务已启动"
        }
    """
```

**Implementation**:
```python
async def _auto_generate_background(article_id: str, title: str, md_path: str, style: str = "zara"):
    """后台任务：自动生成 outline + content"""
    try:
        # Step 1: Generate outline
        await _broadcast_article_update("article_outline_generating", article_id, {
            "step": "outline",
            "progress": 0
        })
        
        result = await _run_xpost("init", md_path, "--topic", title, "--style", style)
        
        if not (result.get("created") or result.get("ok")):
            raise Exception("Outline generation failed")
        
        # Update article with style
        article = _read_article(article_id)
        article["style"] = style
        _write_article(article_id, article)
        
        # Update progress
        await _broadcast_article_update("article_outline_generated", article_id, {
            "step": "outline",
            "progress": 50
        })
        
        # Step 2: Generate content
        await _broadcast_article_update("article_content_generating", article_id, {
            "step": "content",
            "progress": 50
        })
        
        result = await _run_xpost("generate", md_path)
        
        if not result.get("ok"):
            raise Exception("Content generation failed")
        
        # Complete
        content = _read_article_content(article_id)
        article = _read_article(article_id)
        article["content"] = content
        article["step"] = "content"
        article["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_article(article_id, article)
        
        await _broadcast_article_update("article_content_generated", article_id, {
            "content": content,
            "step": "content",
            "progress": 100
        })
        
    except Exception as e:
        await _broadcast_article_update("article_error", article_id, {
            "error": str(e),
            "step": "auto_generation"
        })
```

#### New Endpoint: Upload Image

```python
@app.post("/api/articles/{article_id}/images")
async def upload_article_image(article_id: str, file: UploadFile):
    """
    上传文章图片
    
    Args:
        article_id: 文章 ID
        file: 图片文件
    
    Returns:
        {
            "ok": true,
            "image_url": "/images/articles/art_123/image_456.png",
            "markdown": "![image](/images/articles/art_123/image_456.png)"
        }
    """
```

**Implementation**:
```python
async def upload_article_image(article_id: str, file: UploadFile):
    """上传文章图片到 xinfo/log/articles/{article_id}/images/"""
    # Validate article exists
    article = _read_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create images directory
    images_dir = ARTICLES_DIR / article_id / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    ext = Path(file.filename).suffix
    image_id = int(time.time() * 1000)
    filename = f"image_{image_id}{ext}"
    image_path = images_dir / filename
    
    # Save file
    with open(image_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Update article metadata
    if "images" not in article:
        article["images"] = []
    article["images"].append(filename)
    article["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_article(article_id, article)
    
    # Return relative URL
    image_url = f"/images/articles/{article_id}/{filename}"
    markdown = f"![{filename}]({image_url})"
    
    return {
        "ok": True,
        "image_url": image_url,
        "markdown": markdown
    }
```

```python
@app.post("/api/articles/{article_id}/cancel")
async def cancel_article_generation(article_id: str):
    """
    取消当前正在进行的生成任务
    
    Returns:
        {
            "ok": true,
            "cancelled": true,
            "message": "已取消生成任务"
        }
    """
    return await _kill_active_xpost()
```

### WebSocket Events (Enhanced)

#### New Progress Events

```typescript
// Outline progress
{
  type: "article_outline_progress",
  article_id: "art_123",
  data: {
    progress: 45,  // 0-100
    message: "正在生成大纲...",
    step: "outline"
  },
  timestamp: "2024-01-15T10:30:00Z"
}

// Content progress
{
  type: "article_content_progress",
  article_id: "art_123",
  data: {
    progress: 60,  // 0-100
    message: "正在扩展第 3/5 章节...",
    step: "content",
    current_section: 3,
    total_sections: 5
  },
  timestamp: "2024-01-15T10:35:00Z"
}
```

## Data Models

### Article Metadata (Enhanced)

```typescript
interface Article {
  id: string                    // "art_1234567890123"
  title: string
  status: 'draft' | 'published'
  step: 'title' | 'outline' | 'content' | 'preview'
  
  // Style selection
  style: 'zara' | 'tech' | 'fun'  // Article writing style
  
  // Timestamps
  created_at: string            // ISO 8601
  updated_at: string
  published_at: string | null
  
  // Content
  outline: string               // Markdown outline
  content: string               // Full Markdown content
  md_path: string               // File path
  
  // Publishing
  publish_result: object | null
  
  // New fields for UX
  auto_save_enabled: boolean    // Default: true
  last_auto_saved: string | null
  generation_mode: 'manual' | 'auto'  // Track how it was generated
  
  // Images
  images: string[]              // Array of uploaded image paths
}
```

### Frontend State

```typescript
interface EditorState {
  // Article data
  article: Article | null
  content: string
  
  // Workflow state
  workflowState: {
    mode: 'manual' | 'auto'
    currentStep: 'idle' | 'outline' | 'content' | 'publishing' | 'complete'
    progress: number
    canCancel: boolean
    error: string | null
  }
  
  // UI state
  uiState: {
    previewMode: 'hidden' | 'side' | 'fullscreen'
    saveStatus: 'saved' | 'saving' | 'unsaved' | 'error'
    lastSaved: Date | null
    showProgress: boolean
  }
  
  // Editor state
  editorState: {
    undoStack: string[]
    redoStack: string[]
    hasUnsavedChanges: boolean
  }
}
```

### WebSocket Message Types

```typescript
type ArticleWebSocketMessage = 
  | { type: 'article_created', article_id: string, data: { title: string } }
  | { type: 'article_updated', article_id: string, data: { updated_at: string } }
  | { type: 'article_outline_generating', article_id: string, data: {} }
  | { type: 'article_outline_progress', article_id: string, data: { progress: number, message: string } }
  | { type: 'article_outline_generated', article_id: string, data: { outline: string } }
  | { type: 'article_content_generating', article_id: string, data: {} }
  | { type: 'article_content_progress', article_id: string, data: { progress: number, message: string } }
  | { type: 'article_content_generated', article_id: string, data: { content: string } }
  | { type: 'article_publishing', article_id: string, data: {} }
  | { type: 'article_published', article_id: string, data: { article_url: string } }
  | { type: 'article_error', article_id: string, data: { error: string, step: string } }
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Auto-Generation Workflow Completion

*For any* article in the "title" step, when the user triggers auto-generation, the system should automatically complete both outline generation and content generation in sequence, with each step completing successfully before the next begins, and progress values should increase monotonically from 0 to 100 throughout the process.

**Validates: Requirements FR-1.1, AC-1, FR-1.3, FR-3.3**

### Property 2: Manual Mode Backward Compatibility

*For any* article, the user should be able to generate only the outline, manually edit it, and then separately trigger content generation, with the system preserving all manual edits and completing each step independently.

**Validates: Requirements FR-1.2**

### Property 3: Preview Mode State Transitions

*For any* preview mode state (hidden, side, fullscreen), toggling the preview should cycle through the states in a predictable order, and the current state should persist across page reloads for the same article.

**Validates: Requirements FR-2.2**

### Property 4: Status Notification Completeness

*For any* asynchronous operation (save, generate, publish), the system should display a loading state during execution, followed by either a success notification with confirmation or an error notification with actionable retry options.

**Validates: Requirements FR-3.2, AC-3**

### Property 5: Keyboard Shortcuts and Auto-Save

*For any* content change in the editor, the system should trigger an auto-save after exactly 3 seconds of inactivity, and all keyboard shortcuts (Cmd+S, Cmd+Z, Cmd+Shift+Z, Cmd+P, Cmd+Enter) should execute their corresponding actions without interfering with normal text input.

**Validates: Requirements FR-4.1, FR-4.2, AC-4**

### Property 6: Smart Suggestions Triggering

*For any* article title with length outside the range [10, 100] characters, or content with word count below 500, the system should display a contextual suggestion message indicating the issue and recommended action.

**Validates: Requirements FR-4.3**

### Property 7: Article List Filtering and Sorting

*For any* filter criteria (status, step) and sort order (updated_at, created_at, title), the article list should return only articles matching all active filters, sorted according to the specified order, with consistent results across multiple queries.

**Validates: Requirements FR-5.1, FR-5.2, FR-5.3, AC-5**

### Property 8: WebSocket Reconnection Reliability

*For any* WebSocket disconnection event, the system should automatically attempt to reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s), and upon successful reconnection, should re-subscribe to article updates and sync any missed events.

**Validates: Requirements NFR-3**

### Property 9: Generation Cancellation

*For any* article currently in the generating state (outline or content), when the user triggers cancellation, the system should immediately stop the generation process, preserve any partially generated content, and return the article to an editable state.

**Validates: Requirements FR-1.1 (user can interrupt)**

### Property 10: Content Update Idempotence

*For any* article content, saving the same content multiple times should result in only one updated_at timestamp change (the first save), and subsequent identical saves should be no-ops without triggering WebSocket broadcasts or file writes.

**Validates: Requirements FR-4.2 (auto-save efficiency)**

## Error Handling

### Error Categories

#### 1. Generation Errors

**Scenario**: xpost CLI command fails during outline or content generation

**Handling**:
- Catch exception in background task
- Broadcast `article_error` WebSocket event with detailed error message
- Preserve article in last known good state
- Display error notification with "Retry" button
- Log full error details to server console

**Example**:
```python
try:
    result = await _run_xpost("init", md_path, "--topic", title)
    if not result.get("ok"):
        raise Exception(f"xpost init failed: {result.get('error', 'Unknown error')}")
except Exception as e:
    await _broadcast_article_update("article_error", article_id, {
        "error": str(e),
        "step": "outline_generation",
        "recoverable": True
    })
```

#### 2. WebSocket Disconnection

**Scenario**: Network interruption or server restart

**Handling**:
- Frontend detects `ws.onclose` event
- Display "连接已断开，正在重连..." notification
- Implement exponential backoff reconnection: 1s, 2s, 4s, 8s, 16s, 30s (max)
- On reconnect, fetch latest article state via REST API
- Resume listening for WebSocket events

**Example**:
```typescript
class WebSocketReconnector {
  private reconnectAttempts = 0
  private maxDelay = 30000
  
  async reconnect() {
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxDelay)
    await sleep(delay)
    
    try {
      await this.connect()
      this.reconnectAttempts = 0
      await this.syncState()  // Fetch latest article state
    } catch (e) {
      this.reconnectAttempts++
      this.reconnect()  // Retry
    }
  }
}
```

#### 3. Auto-Save Failures

**Scenario**: Network error or server error during auto-save

**Handling**:
- Display "自动保存失败" notification with warning icon
- Keep content in local state (don't lose user's work)
- Retry save after 10 seconds
- After 3 failed retries, prompt user to manually save
- Store unsaved content in localStorage as backup

**Example**:
```typescript
async autoSave() {
  try {
    await this.saveContent()
    this.saveStatus = 'saved'
    this.lastSaved = new Date()
  } catch (error) {
    this.saveStatus = 'error'
    this.retryCount++
    
    if (this.retryCount < 3) {
      setTimeout(() => this.autoSave(), 10000)
    } else {
      this.showNotification('自动保存失败，请手动保存', 'error')
      localStorage.setItem(`article_backup_${this.articleId}`, this.content)
    }
  }
}
```

#### 4. Concurrent Modification

**Scenario**: Multiple browser tabs editing the same article

**Handling**:
- Not fully prevented in this design (would require operational transformation or CRDTs)
- Mitigation: Show warning when article.updated_at is newer than local version
- Prompt user: "此文章已在其他地方更新，是否重新加载？"
- Provide option to view diff and merge changes

**Example**:
```typescript
async checkForUpdates() {
  const serverArticle = await fetchArticle(this.articleId)
  
  if (serverArticle.updated_at > this.localUpdatedAt) {
    const shouldReload = await this.showConfirmDialog(
      '此文章已在其他地方更新',
      '是否重新加载最新版本？（当前未保存的更改将丢失）'
    )
    
    if (shouldReload) {
      this.loadArticle(this.articleId)
    }
  }
}
```

#### 5. Invalid Input

**Scenario**: User attempts to generate with empty title or invalid data

**Handling**:
- Validate input before making API call
- Show inline validation error message
- Disable action button until input is valid
- Provide helpful error message with correction guidance

**Example**:
```typescript
validateTitle(title: string): ValidationResult {
  if (!title.trim()) {
    return { valid: false, error: '标题不能为空' }
  }
  if (title.length < 10) {
    return { valid: false, error: '标题至少需要 10 个字符' }
  }
  if (title.length > 100) {
    return { valid: false, error: '标题不能超过 100 个字符' }
  }
  return { valid: true }
}
```

### Error Recovery Strategies

| Error Type | Recovery Strategy | User Action Required |
|------------|------------------|---------------------|
| Generation timeout | Automatic retry once, then prompt | Click "Retry" if auto-retry fails |
| Network error | Exponential backoff retry | Wait for reconnection |
| Invalid input | Inline validation | Correct input |
| Server error (5xx) | Retry with backoff | Contact support if persists |
| Concurrent modification | Prompt to reload | Choose version to keep |
| File system error | Log and alert admin | Admin intervention |

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

Together, these provide comprehensive coverage where unit tests catch concrete bugs and property tests verify general correctness.

### Unit Testing

#### Frontend Unit Tests (Vitest + Vue Test Utils)

**Test Files**:
- `WorkflowOrchestrator.test.ts`
- `CompactHeader.test.ts`
- `FloatingActionPanel.test.ts`
- `ProgressIndicator.test.ts`
- `EnhancedMarkdownEditor.test.ts`

**Example Tests**:

```typescript
// WorkflowOrchestrator.test.ts
describe('WorkflowOrchestrator', () => {
  it('should start auto-generation workflow', async () => {
    const orchestrator = new WorkflowOrchestrator(mockArticle)
    await orchestrator.startAutoGeneration()
    
    expect(orchestrator.currentStep).toBe('outline')
    expect(mockApi.post).toHaveBeenCalledWith('/api/articles/art_123/auto-generate')
  })
  
  it('should handle generation errors gracefully', async () => {
    mockApi.post.mockRejectedValue(new Error('Generation failed'))
    const orchestrator = new WorkflowOrchestrator(mockArticle)
    
    await orchestrator.startAutoGeneration()
    
    expect(orchestrator.currentStep).toBe('error')
    expect(orchestrator.error).toBe('Generation failed')
  })
  
  it('should cancel generation when requested', async () => {
    const orchestrator = new WorkflowOrchestrator(mockArticle)
    await orchestrator.startAutoGeneration()
    await orchestrator.cancelGeneration()
    
    expect(mockApi.post).toHaveBeenCalledWith('/api/articles/art_123/cancel')
    expect(orchestrator.currentStep).toBe('idle')
  })
})

// EnhancedMarkdownEditor.test.ts
describe('EnhancedMarkdownEditor', () => {
  it('should trigger auto-save after 3 seconds of inactivity', async () => {
    const editor = mount(EnhancedMarkdownEditor, { props: { modelValue: 'initial' } })
    
    await editor.find('textarea').setValue('updated content')
    
    // Wait for debounce
    await vi.advanceTimersByTime(3000)
    
    expect(mockApi.put).toHaveBeenCalledWith('/api/articles/art_123', {
      content: 'updated content'
    })
  })
  
  it('should handle Cmd+S keyboard shortcut', async () => {
    const editor = mount(EnhancedMarkdownEditor)
    const saveSpy = vi.spyOn(editor.vm, 'saveContent')
    
    await editor.find('textarea').trigger('keydown', { key: 's', metaKey: true })
    
    expect(saveSpy).toHaveBeenCalled()
  })
  
  it('should maintain undo/redo history', async () => {
    const editor = mount(EnhancedMarkdownEditor, { props: { modelValue: 'initial' } })
    
    await editor.find('textarea').setValue('change 1')
    await editor.find('textarea').setValue('change 2')
    
    // Undo
    await editor.find('textarea').trigger('keydown', { key: 'z', metaKey: true })
    expect(editor.vm.content).toBe('change 1')
    
    // Redo
    await editor.find('textarea').trigger('keydown', { key: 'z', metaKey: true, shiftKey: true })
    expect(editor.vm.content).toBe('change 2')
  })
})
```

#### Backend Unit Tests (pytest)

**Test Files**:
- `test_article_api.py`
- `test_article_workflow.py`
- `test_websocket_manager.py`

**Example Tests**:

```python
# test_article_workflow.py
@pytest.mark.asyncio
async def test_auto_generate_workflow():
    """Test one-click auto-generation completes both steps"""
    article_id = "art_test_123"
    
    # Create article
    response = await client.post("/api/articles", json={"title": "Test Article"})
    assert response.json()["ok"] is True
    
    # Start auto-generation
    response = await client.post(f"/api/articles/{article_id}/auto-generate")
    assert response.json()["status"] == "generating"
    
    # Wait for completion (mock WebSocket events)
    await asyncio.sleep(2)  # Simulate generation time
    
    # Verify article state
    response = await client.get(f"/api/articles/{article_id}")
    article = response.json()["article"]
    assert article["step"] == "content"
    assert len(article["content"]) > 0

@pytest.mark.asyncio
async def test_generation_cancellation():
    """Test cancelling generation preserves partial content"""
    article_id = "art_test_456"
    
    # Start generation
    await client.post(f"/api/articles/{article_id}/auto-generate")
    
    # Cancel immediately
    response = await client.post(f"/api/articles/{article_id}/cancel")
    assert response.json()["cancelled"] is True
    
    # Verify article is still editable
    response = await client.get(f"/api/articles/{article_id}")
    article = response.json()["article"]
    assert article["status"] == "draft"

@pytest.mark.asyncio
async def test_websocket_broadcast():
    """Test WebSocket events are broadcast correctly"""
    async with websocket_connect("ws://127.0.0.1:8900/ws/articles") as ws:
        # Trigger article update
        await client.put("/api/articles/art_123", json={"content": "updated"})
        
        # Receive WebSocket message
        message = await ws.receive_json()
        assert message["type"] == "article_updated"
        assert message["article_id"] == "art_123"
```

### Property-Based Testing

**Library**: Use `fast-check` for TypeScript/JavaScript, `hypothesis` for Python

**Configuration**: Each property test should run minimum 100 iterations

**Test Tags**: Each test must reference its design document property

```typescript
// Format: Feature: article-ux-improvement, Property 1: Auto-Generation Workflow Completion
```

#### Property Test Examples

```typescript
// property_tests/workflow.test.ts
import fc from 'fast-check'

describe('Property Tests: Workflow', () => {
  it('Property 1: Auto-generation completes both steps in sequence', async () => {
    // Feature: article-ux-improvement, Property 1: Auto-Generation Workflow Completion
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          title: fc.string({ minLength: 10, maxLength: 100 }),
          articleId: fc.string().map(s => `art_${s}`)
        }),
        async ({ title, articleId }) => {
          const orchestrator = new WorkflowOrchestrator({ id: articleId, title, step: 'title' })
          const events: string[] = []
          
          orchestrator.onStepChange(step => events.push(step))
          
          await orchestrator.startAutoGeneration()
          
          // Verify sequence: outline → content
          expect(events).toEqual(['outline', 'content'])
          expect(orchestrator.currentStep).toBe('complete')
        }
      ),
      { numRuns: 100 }
    )
  })
  
  it('Property 5: Auto-save triggers after exactly 3 seconds', async () => {
    // Feature: article-ux-improvement, Property 5: Keyboard Shortcuts and Auto-Save
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 10000 }),
        async (content) => {
          const editor = new EnhancedMarkdownEditor()
          const saveSpy = vi.fn()
          editor.onSave(saveSpy)
          
          editor.updateContent(content)
          
          // Should not save immediately
          expect(saveSpy).not.toHaveBeenCalled()
          
          // Should save after 3 seconds
          await vi.advanceTimersByTime(3000)
          expect(saveSpy).toHaveBeenCalledOnce()
          expect(saveSpy).toHaveBeenCalledWith(content)
        }
      ),
      { numRuns: 100 }
    )
  })
  
  it('Property 9: Cancellation preserves partial content', async () => {
    // Feature: article-ux-improvement, Property 9: Generation Cancellation
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          articleId: fc.string().map(s => `art_${s}`),
          partialContent: fc.string({ minLength: 0, maxLength: 1000 })
        }),
        async ({ articleId, partialContent }) => {
          const orchestrator = new WorkflowOrchestrator({ id: articleId, step: 'title' })
          
          // Start generation
          const generationPromise = orchestrator.startAutoGeneration()
          
          // Simulate partial content generation
          orchestrator.updatePartialContent(partialContent)
          
          // Cancel
          await orchestrator.cancelGeneration()
          
          // Verify partial content is preserved
          const article = await fetchArticle(articleId)
          expect(article.content).toBe(partialContent)
          expect(article.status).toBe('draft')
        }
      ),
      { numRuns: 100 }
    )
  })
})

// property_tests/list_operations.test.ts
describe('Property Tests: List Operations', () => {
  it('Property 7: Filtering returns only matching articles', async () => {
    // Feature: article-ux-improvement, Property 7: Article List Filtering and Sorting
    await fc.assert(
      fc.asyncProperty(
        fc.array(
          fc.record({
            id: fc.string().map(s => `art_${s}`),
            title: fc.string(),
            status: fc.constantFrom('draft', 'published'),
            step: fc.constantFrom('title', 'outline', 'content', 'preview')
          }),
          { minLength: 0, maxLength: 50 }
        ),
        fc.constantFrom('draft', 'published'),
        async (articles, filterStatus) => {
          // Setup: Create articles
          for (const article of articles) {
            await createArticle(article)
          }
          
          // Filter by status
          const filtered = await getArticles({ status: filterStatus })
          
          // Verify all results match filter
          for (const article of filtered) {
            expect(article.status).toBe(filterStatus)
          }
          
          // Verify no matching articles were excluded
          const expectedCount = articles.filter(a => a.status === filterStatus).length
          expect(filtered.length).toBe(expectedCount)
        }
      ),
      { numRuns: 100 }
    )
  })
})
```

#### Python Property Tests

```python
# test_property_websocket.py
from hypothesis import given, strategies as st
import pytest

@given(
    article_id=st.text(min_size=1, max_size=50).map(lambda s: f"art_{s}"),
    disconnect_count=st.integers(min_value=1, max_value=5)
)
@pytest.mark.asyncio
async def test_property_8_websocket_reconnection(article_id, disconnect_count):
    """
    Feature: article-ux-improvement, Property 8: WebSocket Reconnection Reliability
    
    For any WebSocket disconnection, system should reconnect with exponential backoff
    """
    ws_manager = WebSocketManager("test")
    reconnect_delays = []
    
    for i in range(disconnect_count):
        # Simulate disconnect
        ws_manager.disconnect()
        
        # Attempt reconnect
        delay = await ws_manager.reconnect()
        reconnect_delays.append(delay)
    
    # Verify exponential backoff
    for i in range(1, len(reconnect_delays)):
        expected_delay = min(1000 * (2 ** i), 30000)
        assert reconnect_delays[i] == expected_delay
    
    # Verify final connection is established
    assert ws_manager.is_connected()
```

### Integration Testing

**Scope**: Test complete workflows end-to-end

**Tools**: Playwright for E2E browser testing

**Example**:

```typescript
// e2e/article_workflow.spec.ts
test('complete article workflow: create → generate → publish', async ({ page }) => {
  // Navigate to articles page
  await page.goto('http://localhost:5173/articles')
  
  // Create new article
  await page.click('button:has-text("新建文章")')
  await page.fill('input[placeholder="请输入文章标题"]', 'E2E Test Article')
  await page.click('button:has-text("确定")')
  
  // Wait for editor page
  await page.waitForURL(/\/articles\/art_\d+/)
  
  // Click one-click generation
  await page.click('button:has-text("一键生成")')
  
  // Wait for progress indicator
  await page.waitForSelector('.progress-indicator')
  
  // Wait for completion (max 5 minutes)
  await page.waitForSelector('button:has-text("发布文章")', { timeout: 300000 })
  
  // Verify content was generated
  const content = await page.textContent('.markdown-preview')
  expect(content.length).toBeGreaterThan(500)
  
  // Publish article
  await page.click('button:has-text("发布文章")')
  await page.waitForSelector('.status-badge:has-text("已发布")')
  
  // Verify published status
  const status = await page.textContent('.status-badge')
  expect(status).toBe('已发布')
})
```

### Test Coverage Goals

- **Unit Tests**: > 80% code coverage
- **Property Tests**: All 10 properties implemented
- **Integration Tests**: All critical user flows covered
- **E2E Tests**: Happy path + error scenarios

### Continuous Testing

- Run unit tests on every commit (pre-commit hook)
- Run property tests in CI pipeline
- Run E2E tests nightly
- Monitor test execution time (unit tests < 30s, property tests < 2min)

