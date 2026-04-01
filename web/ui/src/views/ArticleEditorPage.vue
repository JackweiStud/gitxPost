<template>
  <div class="article-editor-page">
    <!-- 紧凑头部 -->
    <CompactHeader
      v-if="article"
      :article-id="article.id"
      :title="article.title"
      :style="article.style || 'zara'"
      :step="article.step"
      :status="article.status"
      :is-generating="isGenerating"
      @update:title="handleTitleUpdate"
      @update:style="handleStyleUpdate"
      @save="handleHeaderSave"
    />

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="article" class="editor-container">
      <!-- 进度指示器 -->
      <ProgressIndicator
        :visible="isGenerating"
        :current-step="currentStep"
        :progress="progress"
        :can-cancel="canCancel"
        @cancel="handleCancelGeneration"
      />

      <!-- 编辑区域 -->
      <div class="editor-main">
        <div class="editor-split">
          <div class="editor-pane">
            <MarkdownEditor
              v-model="content"
              :article-id="article.id"
              :auto-save="true"
              :auto-save-delay="3000"
              @save-status="handleSaveStatus"
            />
          </div>

          <div class="editor-pane">
            <MarkdownPreview :content="content" :article-id="article.id" />
          </div>
        </div>
      </div>

      <!-- 浮动操作面板 -->
      <FloatingActionPanel
        :save-status="saveStatus"
        :last-saved="lastSaved"
        :step="article.step"
        :is-generating="isGenerating"
        :is-publishing="publishing"
        :status="article.status"
        @generate="handleGenerate"
        @publish="handlePublish"
        @toggle-preview="handleTogglePreview"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app.js'
import { useWorkflowOrchestrator } from '../composables/useWorkflowOrchestrator.js'
import CompactHeader from '../components/CompactHeader.vue'
import FloatingActionPanel from '../components/FloatingActionPanel.vue'
import ProgressIndicator from '../components/ProgressIndicator.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import MarkdownPreview from '../components/MarkdownPreview.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const loading = ref(true)
const publishing = ref(false)
const article = ref(null)
const content = ref('')
const saveStatus = ref('saved')
const lastSaved = ref(null)

// 使用 WorkflowOrchestrator
const orchestrator = useWorkflowOrchestrator(route.params.id)
const {
  currentStep,
  progress,
  canCancel,
  selectedStyle,
  isGenerating,
  startAutoGeneration,
  cancelGeneration,
} = orchestrator

// 加载文章
const loadArticle = async () => {
  loading.value = true
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${route.params.id}`)
    const data = await response.json()
    
    if (data.ok) {
      article.value = data.article
      content.value = data.article.content || ''
      
      // 设置选中的风格
      if (data.article.style) {
        selectedStyle.value = data.article.style
      }
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

watch(
  () => route.params.id,
  () => {
    loadArticle()
  },
  { immediate: true }
)

// 处理标题更新
const handleTitleUpdate = (newTitle) => {
  if (article.value) {
    article.value.title = newTitle
  }
}

// 处理风格更新
const handleStyleUpdate = (newStyle) => {
  if (article.value) {
    article.value.style = newStyle
    selectedStyle.value = newStyle
  }
}

// 处理头部保存
const handleHeaderSave = (data) => {
  console.log('Header saved:', data)
}

// 处理保存状态
const handleSaveStatus = (status) => {
  saveStatus.value = status.status
  lastSaved.value = status.lastSaved
}

// 处理一键生成
const handleGenerate = async () => {
  try {
    await startAutoGeneration(selectedStyle.value)
    appStore.notify('生成任务已启动', 'info')
  } catch (error) {
    console.error('启动生成失败:', error)
    appStore.notify('启动生成失败: ' + error.message, 'error')
  }
}

// 处理取消生成
const handleCancelGeneration = async () => {
  try {
    await cancelGeneration()
    appStore.notify('已取消生成', 'info')
  } catch (error) {
    console.error('取消失败:', error)
    appStore.notify('取消失败', 'error')
  }
}

// 处理发布
const handlePublish = async () => {
  if (!confirm('确定要发布这篇文章吗？')) return
  
  publishing.value = true
  
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
    }
  } catch (error) {
    console.error('发布文章失败:', error)
    appStore.notify('发布文章失败', 'error')
    publishing.value = false
  }
}

// 处理预览切换
const handleTogglePreview = () => {
  // TODO: 实现预览模式切换（P1 任务）
  console.log('Toggle preview')
}

// 监听 WebSocket 事件更新内容
const handleWebSocketUpdate = (data) => {
  if (data.article_id !== route.params.id) return
  
  switch (data.type) {
    case 'article_outline_generated':
      content.value = data.data.outline || ''
      article.value.step = 'outline'
      appStore.notify('骨架生成成功', 'success')
      break
      
    case 'article_content_generated':
      content.value = data.data.content || ''
      article.value.step = 'content'
      appStore.notify('全文生成成功', 'success')
      break
      
    case 'article_published':
      publishing.value = false
      article.value.status = 'published'
      article.value.published_at = data.data.published_at
      appStore.notify('文章发布成功', 'success')
      break
      
    case 'article_error':
      publishing.value = false
      appStore.notify(`操作失败: ${data.data.error}`, 'error')
      break
  }
}

onMounted(() => {
  // 监听 WebSocket 消息（通过 orchestrator 的 WebSocket）
  // 注意：orchestrator 已经处理了进度更新，这里只处理内容更新
})

onUnmounted(() => {
  // orchestrator 会自动清理 WebSocket
})
</script>

<style scoped>
.article-editor-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #ffffff);
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary, #9ca3af);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default, #e5e7eb);
  border-top-color: var(--accent-blue, #3b82f6);
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

/* 响应式设计 */
@media (max-width: 1024px) {
  .editor-split {
    grid-template-columns: 1fr;
  }
  
  .editor-pane:last-child {
    display: none;
  }
}

@media (max-width: 768px) {
  .editor-main {
    padding: 12px;
  }
}
</style>
