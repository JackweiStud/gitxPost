<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">发帖</h1>
        <p class="page-subtitle">快速发布 Post</p>
      </div>
    </header>

    <!-- Post Composer -->
    <div class="card composer-card">
      <div class="composer-body">
        <textarea
          v-model="postText"
          class="post-textarea"
          placeholder="说点什么..."
          @input="updateCharCount"
        />

        <!-- Character Count Circle -->
        <div class="char-counter">
          <svg width="60" height="60" class="char-circle">
            <circle
              cx="30"
              cy="30"
              r="25"
              fill="none"
              :stroke="charCountColor"
              stroke-width="4"
              :stroke-dasharray="circumference"
              :stroke-dashoffset="dashOffset"
              transform="rotate(-90 30 30)"
              class="char-circle-progress"
            />
          </svg>
          <div class="char-count-text" :class="{ 'over-limit': charCount > 280 }">
            {{ charCount }}/280
          </div>
        </div>

        <!-- Image Upload Zone -->
        <div
          class="upload-zone"
          :class="{ 'has-images': images.length > 0 }"
          @drop.prevent="handleDrop"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @click="$refs.fileInput.click()"
        >
          <input
            ref="fileInput"
            type="file"
            multiple
            accept="image/*"
            @change="handleFileSelect"
            style="display: none"
          />
          
          <div v-if="images.length === 0" class="upload-prompt">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            <p>拖拽图片到这里，或点击上传</p>
            <p class="upload-hint">最多 4 张图片</p>
          </div>

          <div v-else class="image-grid" @click.stop>
            <div v-for="(img, idx) in images" :key="idx" class="image-item">
              <img :src="img.preview" :alt="img.name" />
              <button class="image-remove" @click="removeImage(idx)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div v-if="images.length < 4" class="image-add" @click="$refs.fileInput.click()">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </div>
          </div>
        </div>

        <!-- Publish Options -->
        <div class="publish-options">
          <div class="option-group">
            <label class="option-label">发布时间</label>
            <div class="time-toggle">
              <button
                class="toggle-btn"
                :class="{ active: !isScheduled }"
                @click="isScheduled = false"
              >
                立即发布
              </button>
              <button
                class="toggle-btn"
                :class="{ active: isScheduled }"
                @click="isScheduled = true"
              >
                定时发布
              </button>
            </div>
          </div>

          <div v-if="isScheduled" class="scheduled-time">
            <input
              type="datetime-local"
              v-model="scheduledTime"
              class="time-input"
              :min="minDateTime"
            />
          </div>
        </div>

        <!-- Actions -->
        <div class="composer-actions">
          <button class="btn btn-ghost" @click="clearForm">清空</button>
          <button
            class="btn btn-primary"
            @click="handlePublish"
            :disabled="!canPublish || isPublishing"
          >
            <svg v-if="!isPublishing" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            <div v-else class="spinner-small"></div>
            {{ isPublishing ? '发布中...' : (isScheduled ? '加入队列' : '立即发布') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Publish Queue -->
    <PublishQueue
      :queue="publishQueue"
      @cancel="handleCancel"
      @retry="handleRetry"
      @delete="handleDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'
import PublishQueue from '../components/PublishQueue.vue'

const appStore = useAppStore()

const postText = ref('')
const charCount = ref(0)
const images = ref([])
const isDragging = ref(false)
const isScheduled = ref(false)
const scheduledTime = ref('')
const isPublishing = ref(false)
const publishQueue = ref([])
let wsConnection = null

const circumference = 2 * Math.PI * 25

const dashOffset = computed(() => {
  const ratio = charCount.value / 280
  return circumference * (1 - ratio)
})

const charCountColor = computed(() => {
  if (charCount.value > 280) return 'var(--accent-red)'
  if (charCount.value > 250) return 'var(--accent-amber)'
  return 'var(--accent-green)'
})

const canPublish = computed(() => {
  return postText.value.trim().length > 0 && charCount.value <= 280
})

const minDateTime = computed(() => {
  const now = new Date()
  now.setMinutes(now.getMinutes() + 1)
  return now.toISOString().slice(0, 16)
})

function updateCharCount() {
  charCount.value = postText.value.length
}

function handleDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  addImages(files)
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files)
  addImages(files)
  e.target.value = ''
}

function addImages(files) {
  const imageFiles = files.filter(f => f.type.startsWith('image/'))
  
  if (images.value.length + imageFiles.length > 4) {
    appStore.notify('最多上传 4 张图片', 'error')
    return
  }
  
  imageFiles.forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      images.value.push({
        file,
        preview: e.target.result,
        name: file.name
      })
    }
    reader.readAsDataURL(file)
  })
}

function removeImage(index) {
  images.value.splice(index, 1)
}

function clearForm() {
  postText.value = ''
  charCount.value = 0
  images.value = []
  isScheduled.value = false
  scheduledTime.value = ''
}

async function handlePublish() {
  if (!canPublish.value) return
  
  isPublishing.value = true
  
  try {
    // 上传图片到服务器
    const imagePaths = []
    if (images.value.length > 0) {
      appStore.notify('正在上传图片...', 'info')
      for (const img of images.value) {
        try {
          const result = await api.uploadImage(img.file)
          if (result.ok && result.path) {
            imagePaths.push(result.path)
          }
        } catch (e) {
          appStore.notify(`图片上传失败: ${e.message}`, 'error')
          isPublishing.value = false
          return
        }
      }
    }
    
    const payload = {
      text: postText.value,
      images: imagePaths,
      publish: true,
      scheduled_at: isScheduled.value && scheduledTime.value
        ? new Date(scheduledTime.value).toISOString()
        : null
    }
    
    const result = await api.publishPost(payload)
    
    if (result.ok) {
      if (result.mode === 'immediate') {
        appStore.notify('发布成功', 'success')
      } else {
        appStore.notify('已加入发布队列', 'success')
      }
      clearForm()
      await loadQueue()
    } else {
      appStore.notify(result.error || '发布失败', 'error')
    }
  } catch (e) {
    appStore.notify('发布失败: ' + e.message, 'error')
  } finally {
    isPublishing.value = false
  }
}

async function loadQueue() {
  try {
    const result = await api.getPublishQueue()
    if (result.ok) {
      publishQueue.value = result.queue || []
    }
  } catch (e) {
    console.error('加载队列失败:', e)
  }
}

function connectWebSocket() {
  if (wsConnection) return
  
  // 使用相对路径，通过 Vite 代理连接
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host  // 包含端口号
  const wsUrl = `${protocol}//${host}/ws/queue`
  
  console.log('🔌 连接 WebSocket:', wsUrl)
  wsConnection = new WebSocket(wsUrl)
  
  wsConnection.onopen = () => {
    console.log('✅ WebSocket 已连接')
  }
  
  wsConnection.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      console.log('📨 收到 WebSocket 消息:', data.type)
      
      if (data.type === 'initial') {
        // 初始队列数据
        publishQueue.value = data.queue || []
      } else if (data.type === 'task_added') {
        // 新任务添加
        publishQueue.value.push(data.task)
      } else if (data.type === 'task_completed' || data.type === 'task_failed') {
        // 任务状态更新
        const index = publishQueue.value.findIndex(t => t.id === data.task_id)
        if (index !== -1) {
          publishQueue.value[index] = data.task
        }
      }
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
    // 3 秒后重连
    setTimeout(() => {
      if (!wsConnection) {
        connectWebSocket()
      }
    }, 3000)
  }
}

function disconnectWebSocket() {
  if (wsConnection) {
    wsConnection.close()
    wsConnection = null
  }
}

async function handleCancel(taskId) {
  try {
    await api.cancelPublishTask(taskId)
    appStore.notify('已取消任务', 'success')
    await loadQueue()
  } catch (e) {
    appStore.notify('取消失败: ' + e.message, 'error')
  }
}

async function handleRetry(taskId) {
  try {
    await api.retryPublishTask(taskId)
    appStore.notify('任务已重新加入队列', 'success')
    await loadQueue()
  } catch (e) {
    appStore.notify('重试失败: ' + e.message, 'error')
  }
}

async function handleDelete(taskId) {
  if (!confirm('确定要删除这条记录吗？')) return
  
  try {
    await api.deletePublishTask(taskId)
    appStore.notify('已删除', 'success')
    await loadQueue()
  } catch (e) {
    appStore.notify('删除失败: ' + e.message, 'error')
  }
}

onMounted(() => {
  loadQueue()
  connectWebSocket()
  
  // 设置默认定时时间为 1 小时后
  const defaultTime = new Date()
  defaultTime.setHours(defaultTime.getHours() + 1)
  scheduledTime.value = defaultTime.toISOString().slice(0, 16)
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.page {
  padding: 32px 40px;
  max-width: 900px;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.page-subtitle {
  color: var(--text-tertiary);
  font-size: 13px;
  margin-top: 4px;
}

.composer-card {
  margin-bottom: 24px;
}

.composer-body {
  padding: 24px;
}

.post-textarea {
  width: 100%;
  min-height: 120px;
  padding: 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: 15px;
  line-height: 1.5;
  color: var(--text-primary);
  resize: vertical;
  font-family: inherit;
  transition: border-color var(--transition-fast);
}

.post-textarea:focus {
  outline: none;
  border-color: var(--accent-blue);
}

.post-textarea::placeholder {
  color: var(--text-tertiary);
}

.char-counter {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 16px 0;
  position: relative;
}

.char-circle {
  transform: rotate(0deg);
}

.char-circle-progress {
  transition: stroke-dashoffset 0.3s ease, stroke 0.3s ease;
}

.char-count-text {
  position: absolute;
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}

.char-count-text.over-limit {
  color: var(--accent-red);
}

.upload-zone {
  margin: 16px 0;
  padding: 32px;
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-md);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.upload-zone:hover {
  border-color: var(--accent-blue);
  background: var(--bg-hover);
}

.upload-zone.has-images {
  padding: 16px;
}

.upload-prompt {
  color: var(--text-tertiary);
}

.upload-prompt svg {
  margin-bottom: 12px;
  opacity: 0.5;
}

.upload-prompt p {
  margin: 4px 0;
  font-size: 13px;
}

.upload-hint {
  font-size: 11px;
  opacity: 0.7;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.image-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-tertiary);
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border-radius: 50%;
  opacity: 0;
  transition: opacity var(--transition-fast);
  padding: 0;
}

.image-item:hover .image-remove {
  opacity: 1;
}

.image-add {
  aspect-ratio: 1;
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.image-add:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: var(--bg-hover);
}

.publish-options {
  margin: 24px 0;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.option-group {
  margin-bottom: 12px;
}

.option-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.time-toggle {
  display: inline-flex;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.toggle-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  background: transparent;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.toggle-btn.active {
  background: var(--accent-blue);
  color: white;
}

.scheduled-time {
  margin-top: 12px;
}

.time-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.time-input:focus {
  outline: none;
  border-color: var(--accent-blue);
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .image-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
