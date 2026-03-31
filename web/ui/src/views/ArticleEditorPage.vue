<template>
  <div class="article-editor-page">
    <div class="editor-header">
      <button class="btn-back" @click="goBack">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        返回
      </button>
      
      <h1 class="article-title">{{ article?.title || '加载中...' }}</h1>
      
      <div class="header-actions">
        <span class="status-badge" :class="'status-' + article?.status">
          {{ article?.status === 'draft' ? '草稿' : '已发布' }}
        </span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="article" class="editor-container">
      <!-- 工作流步骤 -->
      <div class="workflow-steps">
        <div
          v-for="(stepInfo, index) in steps"
          :key="stepInfo.value"
          class="step-item"
          :class="{
            active: article.step === stepInfo.value,
            completed: getStepIndex(article.step) > index
          }"
        >
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-label">{{ stepInfo.label }}</div>
        </div>
      </div>

      <!-- 编辑区域 -->
      <div class="editor-main">
        <div class="editor-split">
          <div class="editor-pane">
            <div class="pane-header">
              <h3>编辑器</h3>
              <div class="pane-actions">
                <button class="btn-sm" @click="saveContent" :disabled="saving">
                  {{ saving ? '保存中...' : '保存草稿' }}
                </button>
                <button
                  v-if="article.step === 'title'"
                  class="btn-sm btn-primary"
                  @click="generateOutline"
                  :disabled="generating"
                >
                  {{ generating ? '生成中...' : '生成骨架' }}
                </button>
                <button
                  v-if="article.step === 'outline'"
                  class="btn-sm btn-primary"
                  @click="generateContent"
                  :disabled="generating"
                >
                  {{ generating ? '生成中...' : '生成全文' }}
                </button>
                <button
                  v-if="article.step === 'content'"
                  class="btn-sm btn-success"
                  @click="publishArticle"
                  :disabled="publishing"
                >
                  {{ publishing ? '发布中...' : '发布文章' }}
                </button>
              </div>
            </div>
            <MarkdownEditor v-model="content" />
          </div>

          <div class="editor-pane">
            <div class="pane-header">
              <h3>预览</h3>
            </div>
            <MarkdownPreview :content="content" />
          </div>
        </div>
      </div>

      <!-- 状态消息 -->
      <div v-if="statusMessage" class="status-message" :class="'status-' + statusMessage.type">
        {{ statusMessage.text }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app.js'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import MarkdownPreview from '../components/MarkdownPreview.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const loading = ref(true)
const saving = ref(false)
const generating = ref(false)
const publishing = ref(false)
const article = ref(null)
const content = ref('')
const statusMessage = ref(null)
let ws = null

const steps = [
  { value: 'title', label: '标题' },
  { value: 'outline', label: '骨架' },
  { value: 'content', label: '内容' },
  { value: 'preview', label: '预览' }
]

const getStepIndex = (step) => {
  return steps.findIndex(s => s.value === step)
}

// 加载文章
const loadArticle = async () => {
  loading.value = true
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${route.params.id}`)
    const data = await response.json()
    
    if (data.ok) {
      article.value = data.article
      content.value = data.article.content || ''
    } else {
      appStore.notify('加载文章失败', 'error')
      router.push('/articles')
    }
  } catch (error) {
    console.error('加载文章失败:', error)
    appStore.notify('加载文章失败', 'error')
    router.push('/articles')
  } finally {
    loading.value = false
  }
}

// 保存内容
const saveContent = async () => {
  saving.value = true
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${route.params.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content.value })
    })
    
    const data = await response.json()
    
    if (data.ok) {
      appStore.notify('保存成功', 'success')
      article.value.updated_at = data.updated_at
    } else {
      appStore.notify(data.error || '保存失败', 'error')
    }
  } catch (error) {
    console.error('保存失败:', error)
    appStore.notify('保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 生成骨架
const generateOutline = async () => {
  generating.value = true
  statusMessage.value = { type: 'info', text: '正在生成骨架...' }
  
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${route.params.id}/outline`, {
      method: 'POST'
    })
    
    const data = await response.json()
    
    if (data.ok) {
      appStore.notify('骨架生成任务已启动', 'info')
    } else {
      appStore.notify(data.error || '启动失败', 'error')
      generating.value = false
      statusMessage.value = null
    }
  } catch (error) {
    console.error('生成骨架失败:', error)
    appStore.notify('生成骨架失败', 'error')
    generating.value = false
    statusMessage.value = null
  }
}

// 生成全文
const generateContent = async () => {
  generating.value = true
  statusMessage.value = { type: 'info', text: '正在生成全文...' }
  
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${route.params.id}/generate`, {
      method: 'POST'
    })
    
    const data = await response.json()
    
    if (data.ok) {
      appStore.notify('全文生成任务已启动', 'info')
    } else {
      appStore.notify(data.error || '启动失败', 'error')
      generating.value = false
      statusMessage.value = null
    }
  } catch (error) {
    console.error('生成全文失败:', error)
    appStore.notify('生成全文失败', 'error')
    generating.value = false
    statusMessage.value = null
  }
}

// 发布文章
const publishArticle = async () => {
  if (!confirm('确定要发布这篇文章吗？')) return
  
  publishing.value = true
  statusMessage.value = { type: 'info', text: '正在发布文章...' }
  
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${route.params.id}/publish`, {
      method: 'POST'
    })
    
    const data = await response.json()
    
    if (data.ok) {
      appStore.notify('文章发布任务已启动', 'info')
    } else {
      appStore.notify(data.error || '启动失败', 'error')
      publishing.value = false
      statusMessage.value = null
    }
  } catch (error) {
    console.error('发布文章失败:', error)
    appStore.notify('发布文章失败', 'error')
    publishing.value = false
    statusMessage.value = null
  }
}

// WebSocket 连接
const connectWebSocket = () => {
  ws = new WebSocket('ws://127.0.0.1:8900/ws/articles')
  
  ws.onopen = () => {
    console.log('WebSocket 已连接')
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    // 只处理当前文章的事件
    if (data.article_id !== route.params.id) return
    
    switch (data.type) {
      case 'article_outline_generated':
        generating.value = false
        statusMessage.value = { type: 'success', text: '骨架生成成功！' }
        content.value = data.data.outline || ''
        article.value.step = 'outline'
        appStore.notify('骨架生成成功', 'success')
        setTimeout(() => { statusMessage.value = null }, 3000)
        break
        
      case 'article_content_generated':
        generating.value = false
        statusMessage.value = { type: 'success', text: '全文生成成功！' }
        content.value = data.data.content || ''
        article.value.step = 'content'
        appStore.notify('全文生成成功', 'success')
        setTimeout(() => { statusMessage.value = null }, 3000)
        break
        
      case 'article_published':
        publishing.value = false
        statusMessage.value = { type: 'success', text: '文章发布成功！' }
        article.value.status = 'published'
        article.value.published_at = data.data.published_at
        appStore.notify('文章发布成功', 'success')
        setTimeout(() => { statusMessage.value = null }, 3000)
        break
        
      case 'article_error':
        generating.value = false
        publishing.value = false
        statusMessage.value = { type: 'error', text: `错误: ${data.data.error}` }
        appStore.notify(`操作失败: ${data.data.error}`, 'error')
        break
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket 错误:', error)
  }
  
  ws.onclose = () => {
    console.log('WebSocket 已断开')
  }
}

const goBack = () => {
  router.push('/articles')
}

onMounted(() => {
  loadArticle()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.article-editor-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-secondary);
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: var(--radius-md);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.btn-back:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.article-title {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
}

.status-draft {
  background: rgba(255, 193, 7, 0.15);
  color: #f57c00;
}

.status-published {
  background: rgba(76, 175, 80, 0.15);
  color: #2e7d32;
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workflow-steps {
  display: flex;
  gap: 8px;
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-default);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  font-size: 13px;
  font-weight: 500;
}

.step-item.active {
  background: linear-gradient(90deg, rgba(26, 115, 232, 0.15), rgba(0, 201, 167, 0.1));
  color: var(--accent-blue);
  border: 1px solid rgba(26, 115, 232, 0.3);
}

.step-item.completed {
  background: rgba(76, 175, 80, 0.1);
  color: #2e7d32;
}

.step-number {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: currentColor;
  color: white;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 600;
  opacity: 0.8;
}

.editor-main {
  flex: 1;
  overflow: hidden;
  padding: 20px 24px;
}

.editor-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  height: 100%;
}

.editor-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.pane-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.pane-actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.btn-sm:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm.btn-primary {
  background: var(--accent-blue);
  color: white;
}

.btn-sm.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-sm.btn-success {
  background: var(--accent-green);
  color: white;
}

.btn-sm.btn-success:hover:not(:disabled) {
  background: #2e7d32;
}

.status-message {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  z-index: 1000;
}

.status-message.status-info {
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid rgba(21, 101, 192, 0.3);
}

.status-message.status-success {
  background: #e6f4ea;
  color: #137333;
  border: 1px solid rgba(30, 142, 62, 0.3);
}

.status-message.status-error {
  background: #fce8e6;
  color: #c5221f;
  border: 1px solid rgba(217, 48, 37, 0.3);
}
</style>
