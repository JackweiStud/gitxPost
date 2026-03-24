<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">设置</h1>
        <p class="page-subtitle">管理你的兴趣画像和偏好设置</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" @click="resetChanges" :disabled="!hasChanges || saving">
          重置
        </button>
        <button class="btn btn-primary" @click="saveChanges" :disabled="!hasChanges || saving">
          <svg v-if="saving" class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>
          {{ saving ? '保存中...' : '保存修改' }}
        </button>
      </div>
    </header>

    <div class="settings-content">
      <div v-if="loading" class="loading-state">
        <div class="loader"></div>
        <span>加载中...</span>
      </div>

      <div v-else class="interests-editor card">
        <div class="card-header">
          <h2>🎯 兴趣画像</h2>
          <span class="updated-at" v-if="updatedAt">最后更新：{{ updatedAt }}</span>
        </div>

        <div class="editor-sections">
          <!-- Focus Section -->
          <div class="editor-section">
            <div class="section-header">
              <div class="section-title">
                <span class="section-icon">🔍</span>
                <span class="section-name">关注主题</span>
                <span class="section-count">({{ focus.length }})</span>
              </div>
              <p class="section-desc">AI 日报会优先筛选这些方向的内容</p>
            </div>
            <div class="tag-list">
              <div v-for="(item, idx) in focus" :key="'focus-' + idx" class="tag-item">
                <input 
                  v-model="focus[idx]" 
                  class="tag-input"
                  @input="markChanged"
                  @keydown.enter="$event.target.blur()"
                />
                <button class="tag-remove" @click="removeItem(focus, idx)" aria-label="删除">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
              <button class="tag-add" @click="addItem(focus, '新关注主题')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                添加关注主题
              </button>
            </div>
          </div>

          <!-- Recent Context Section -->
          <div class="editor-section">
            <div class="section-header">
              <div class="section-title">
                <span class="section-icon">📋</span>
                <span class="section-name">近期关注</span>
                <span class="section-count">({{ recentContext.length }})</span>
              </div>
              <p class="section-desc">你当前的工作重点和关注方向</p>
            </div>
            <div class="tag-list">
              <div v-for="(item, idx) in recentContext" :key="'context-' + idx" class="tag-item">
                <input 
                  v-model="recentContext[idx]" 
                  class="tag-input"
                  @input="markChanged"
                  @keydown.enter="$event.target.blur()"
                />
                <button class="tag-remove" @click="removeItem(recentContext, idx)" aria-label="删除">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
              <button class="tag-add" @click="addItem(recentContext, '新近期关注')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                添加近期关注
              </button>
            </div>
          </div>

          <!-- Ignore Section -->
          <div class="editor-section">
            <div class="section-header">
              <div class="section-title">
                <span class="section-icon">🚫</span>
                <span class="section-name">忽略主题</span>
                <span class="section-count">({{ ignore.length }})</span>
              </div>
              <p class="section-desc">AI 日报会跳过这些类型的内容</p>
            </div>
            <div class="tag-list">
              <div v-for="(item, idx) in ignore" :key="'ignore-' + idx" class="tag-item tag-item-danger">
                <input 
                  v-model="ignore[idx]" 
                  class="tag-input"
                  @input="markChanged"
                  @keydown.enter="$event.target.blur()"
                />
                <button class="tag-remove" @click="removeItem(ignore, idx)" aria-label="删除">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
              <button class="tag-add" @click="addItem(ignore, '新忽略主题')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                添加忽略主题
              </button>
            </div>
          </div>

          <!-- Preferred Formats Section -->
          <div class="editor-section">
            <div class="section-header">
              <div class="section-title">
                <span class="section-icon">📄</span>
                <span class="section-name">偏好格式</span>
                <span class="section-count">({{ preferredFormats.length }})</span>
              </div>
              <p class="section-desc">你偏好的内容形式和深度</p>
            </div>
            <div class="tag-list">
              <div v-for="(item, idx) in preferredFormats" :key="'format-' + idx" class="tag-item">
                <input 
                  v-model="preferredFormats[idx]" 
                  class="tag-input"
                  @input="markChanged"
                  @keydown.enter="$event.target.blur()"
                />
                <button class="tag-remove" @click="removeItem(preferredFormats, idx)" aria-label="删除">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
              <button class="tag-add" @click="addItem(preferredFormats, '新偏好格式')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                添加偏好格式
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const router = useRouter()
const appStore = useAppStore()

const loading = ref(false)
const saving = ref(false)
const hasChanges = ref(false)
const updatedAt = ref('')

const focus = ref([])
const recentContext = ref([])
const ignore = ref([])
const preferredFormats = ref([])

const original = ref({})

async function loadInterests() {
  loading.value = true
  try {
    const data = await api.getInterests()
    focus.value = [...(data.focus || [])]
    recentContext.value = [...(data.recent_context || [])]
    ignore.value = [...(data.ignore || [])]
    preferredFormats.value = [...(data.preferred_formats || [])]
    updatedAt.value = data._updated || ''
    
    // Save original for reset
    original.value = {
      focus: [...focus.value],
      recentContext: [...recentContext.value],
      ignore: [...ignore.value],
      preferredFormats: [...preferredFormats.value],
    }
    
    hasChanges.value = false
  } catch (e) {
    appStore.notify('加载兴趣画像失败: ' + e.message, 'error')
  } finally {
    loading.value = false
  }
}

function markChanged() {
  hasChanges.value = true
}

function addItem(list, placeholder) {
  list.push(placeholder)
  markChanged()
  // Focus the new input after next tick
  setTimeout(() => {
    const inputs = document.querySelectorAll('.tag-input')
    const lastInput = inputs[inputs.length - 1]
    if (lastInput) {
      lastInput.focus()
      lastInput.select()
    }
  }, 50)
}

function removeItem(list, index) {
  list.splice(index, 1)
  markChanged()
}

function resetChanges() {
  focus.value = [...original.value.focus]
  recentContext.value = [...original.value.recentContext]
  ignore.value = [...original.value.ignore]
  preferredFormats.value = [...original.value.preferredFormats]
  hasChanges.value = false
}

async function saveChanges() {
  saving.value = true
  try {
    const result = await api.updateInterests({
      focus: focus.value,
      recent_context: recentContext.value,
      ignore: ignore.value,
      preferred_formats: preferredFormats.value,
    })
    
    appStore.notify('兴趣画像已保存', 'success')
    updatedAt.value = result.updated_at
    hasChanges.value = false
    
    // Update original
    original.value = {
      focus: [...focus.value],
      recentContext: [...recentContext.value],
      ignore: [...ignore.value],
      preferredFormats: [...preferredFormats.value],
    }
  } catch (e) {
    appStore.notify('保存失败: ' + e.message, 'error')
  } finally {
    saving.value = false
  }
}

// Route guard for unsaved changes
onBeforeRouteLeave((to, from, next) => {
  if (hasChanges.value) {
    const answer = window.confirm('有未保存的修改，确定离开？')
    if (answer) {
      next()
    } else {
      next(false)
    }
  } else {
    next()
  }
})

// Warn before page unload
function handleBeforeUnload(e) {
  if (hasChanges.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  loadInterests()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style scoped>
.page {
  padding: 32px 40px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-shrink: 0;
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

.header-actions {
  display: flex;
  gap: 8px;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 40px 20px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.loader {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-default);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner {
  animation: spin 0.8s linear infinite;
}

.interests-editor {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 24px;
}

.card-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.updated-at {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.editor-sections {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.editor-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-icon {
  font-size: 18px;
}

.section-count {
  font-size: 13px;
  color: var(--text-tertiary);
  font-weight: 400;
}

.section-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 0;
  padding-left: 26px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 6px 8px 6px 12px;
  transition: all var(--transition-fast);
  max-width: 100%;
}

.tag-item:hover {
  border-color: var(--accent-blue);
  background: var(--bg-tertiary);
}

.tag-item-danger {
  border-color: rgba(239, 68, 68, 0.3);
}

.tag-item-danger:hover {
  border-color: #ef4444;
}

.tag-input {
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
  padding: 0;
  outline: none;
  min-width: 120px;
  flex: 1;
}

.tag-input:focus {
  outline: none;
}

.tag-remove {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  padding: 0;
}

.tag-remove:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.tag-add {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.tag-add:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.05);
  border-style: solid;
}
</style>
