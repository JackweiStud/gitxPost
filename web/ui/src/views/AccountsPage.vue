<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">关注账号</h1>
        <p class="page-subtitle">管理 X 雷达监控账号</p>
      </div>
      <div class="header-actions">
        <button
          class="btn btn-ghost"
          @click="handleFollowingSync"
          :disabled="syncingFollowing"
          title=".venv/bin/python xpost.py following-sync jackaiwison --timeout 45 --idle-rounds 20"
        >
          <svg
            v-if="!syncingFollowing"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
            <path d="M3 21v-5h5"/>
            <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
            <path d="M21 3v5h-5"/>
          </svg>
          <span v-else class="btn-spinner"></span>
          {{ syncingFollowing ? '同步中...' : '同步 Following' }}
        </button>
        <button class="btn btn-primary" @click="showAddDialog = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          添加账号
        </button>
      </div>
    </header>

    <div class="accounts-content">
      <!-- Search Bar -->
      <div class="search-bar">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input 
          v-model="searchQuery" 
          type="text" 
          class="search-input" 
          placeholder="搜索账号..."
        />
      </div>

      <div v-if="loading" class="loading-state">
        <div class="loader"></div>
        <span>加载中...</span>
      </div>

      <div v-else class="accounts-layout">
        <!-- Active Accounts -->
        <div class="accounts-section">
          <div class="section-header">
            <h2>活跃账号</h2>
            <span class="count-badge">{{ filteredActive.length }}</span>
            <span
              class="language-summary-badge"
              :title="languageSummaryTitle"
            >
              CN {{ activeChinesePercentText }}
            </span>
          </div>
          <div class="accounts-table">
            <div v-if="!filteredActive.length" class="empty-state">
              <svg class="empty-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
              </svg>
              <p>{{ searchQuery ? '未找到匹配的账号' : '暂无活跃账号' }}</p>
            </div>
            <div v-else class="account-list">
              <div 
                v-for="account in filteredActive" 
                :key="account.handle" 
                class="account-item"
              >
                <div class="account-info">
                  <span class="account-handle">@{{ account.handle }}</span>
                  <span
                    class="language-badge"
                    :class="languageBadgeClass(account)"
                    :title="languageBadgeTitle(account)"
                  >
                    {{ account.language_label || '--' }}
                  </span>
                  <span class="account-status status-active">活跃</span>
                </div>
                <button 
                  class="btn btn-sm btn-ghost btn-danger" 
                  @click="confirmRemove(account.handle)"
                  :disabled="removing === account.handle"
                >
                  {{ removing === account.handle ? '移除中...' : '移除' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Removed Accounts -->
        <div class="accounts-section">
          <div class="section-header">
            <h2>已移除账号</h2>
            <span class="count-badge">{{ filteredRemoved.length }}</span>
          </div>
          <div class="accounts-table">
            <div v-if="!filteredRemoved.length" class="empty-state">
              <svg class="empty-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
              </svg>
              <p>{{ searchQuery ? '未找到匹配的账号' : '暂无已移除账号' }}</p>
            </div>
            <div v-else class="account-list">
              <div 
                v-for="account in filteredRemoved" 
                :key="account.handle" 
                class="account-item"
              >
                <div class="account-info">
                  <span class="account-handle">@{{ account.handle }}</span>
                  <span
                    class="language-badge"
                    :class="languageBadgeClass(account)"
                    :title="languageBadgeTitle(account)"
                  >
                    {{ account.language_label || '--' }}
                  </span>
                  <span class="account-status status-removed">已移除</span>
                </div>
                <button 
                  class="btn btn-sm btn-ghost" 
                  @click="handleRestore(account.handle)"
                  :disabled="restoring === account.handle"
                >
                  {{ restoring === account.handle ? '恢复中...' : '恢复' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Account Dialog -->
    <div v-if="showAddDialog" class="dialog-overlay" @click="closeAddDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3>添加监控账号</h3>
          <button class="dialog-close" @click="closeAddDialog" aria-label="关闭">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label class="form-label">Handle</label>
            <div class="input-with-prefix">
              <span class="input-prefix">@</span>
              <input 
                v-model="addForm.handle" 
                type="text" 
                class="form-input"
                placeholder="username"
                @keydown.enter="handleAdd"
                ref="handleInput"
              />
            </div>
            <p class="form-hint">X (Twitter) 账号用户名</p>
          </div>
          <div class="form-group">
            <label class="form-label">备注</label>
            <input 
              v-model="addForm.note" 
              type="text" 
              class="form-input"
              placeholder="例如：AI 研究者，多方推荐"
              @keydown.enter="handleAdd"
            />
            <p class="form-hint">添加原因或账号特点（必填）</p>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-ghost" @click="closeAddDialog" :disabled="addSubmitting">
            取消
          </button>
          <button 
            class="btn btn-primary" 
            @click="handleAdd"
            :disabled="!canSubmitAdd || addSubmitting"
          >
            {{ addSubmitting ? '添加中...' : '确认添加' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, reactive, nextTick, watch } from 'vue'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const appStore = useAppStore()

const accounts = ref([])
const languageSummary = ref(null)
const loading = ref(false)
const searchQuery = ref('')
const removing = ref(null)
const restoring = ref(null)
const syncingFollowing = ref(false)

const showAddDialog = ref(false)
const addForm = reactive({ handle: '', note: '' })
const addSubmitting = ref(false)
const handleInput = ref(null)

const activeAccounts = computed(() => 
  accounts.value.filter(a => a.status === 'active')
)

const removedAccounts = computed(() => 
  accounts.value.filter(a => a.status === 'removed')
)

const filteredActive = computed(() => {
  if (!searchQuery.value) return activeAccounts.value
  const q = searchQuery.value.toLowerCase()
  return activeAccounts.value.filter(a => 
    a.handle.toLowerCase().includes(q)
  )
})

const filteredRemoved = computed(() => {
  if (!searchQuery.value) return removedAccounts.value
  const q = searchQuery.value.toLowerCase()
  return removedAccounts.value.filter(a => 
    a.handle.toLowerCase().includes(q)
  )
})

const canSubmitAdd = computed(() => {
  return addForm.handle.trim() && addForm.note.trim()
})

const activeChinesePercentText = computed(() => {
  const value = languageSummary.value?.chinese_percent
  return typeof value === 'number' ? `${value.toFixed(1)}%` : '--'
})

const languageSummaryTitle = computed(() => {
  const summary = languageSummary.value
  if (!summary) return '尚未计算'
  const time = summary.latest_scan_time || '暂无扫描时间'
  return `基于最新 3 条去重帖子计算；页面打开/刷新时更新，不触发扫描。最新扫描：${time}`
})

function languageBadgeClass(account) {
  return {
    'language-badge-en': account.language === 'en',
    'language-badge-cn': account.language === 'zh',
    'language-badge-unknown': !['en', 'zh'].includes(account.language),
  }
}

function languageBadgeTitle(account) {
  const counts = account.language_post_counts || {}
  const sampleCount = account.language_sample_count ?? 0
  return `最新 ${sampleCount} 条：EN ${counts.en || 0} / CN ${counts.zh || 0} / Other ${counts.other || 0} / Unknown ${counts.unknown || 0}`
}

async function loadAccounts() {
  loading.value = true
  try {
    const data = await api.getRadarAccounts()
    accounts.value = data.accounts || []
    languageSummary.value = data.language_summary || null
  } catch (e) {
    appStore.notify('加载账号列表失败: ' + e.message, 'error')
  } finally {
    loading.value = false
  }
}

function confirmRemove(handle) {
  const confirmed = window.confirm(`确定要移除 @${handle} 吗？\n\n账号将被注释保留，可随时恢复。`)
  if (confirmed) {
    handleRemove(handle)
  }
}

async function handleRemove(handle) {
  removing.value = handle
  try {
    const result = await api.removeRadarAccount(handle)
    
    // Check for warnings in stdout
    const stdout = result.stdout || ''
    if (stdout.includes('⚠️') || stdout.includes('不在活跃列表')) {
      appStore.notify(`@${handle} 未在活跃列表中`, 'error')
    } else if (result.ok) {
      appStore.notify(`已移除 @${handle}`, 'success')
      await loadAccounts()
    } else {
      appStore.notify('移除失败: ' + (result.stderr || '未知错误'), 'error')
    }
  } catch (e) {
    appStore.notify('移除失败: ' + e.message, 'error')
  } finally {
    removing.value = null
  }
}

async function handleRestore(handle) {
  restoring.value = handle
  try {
    const result = await api.restoreRadarAccount(handle)
    
    const stdout = result.stdout || ''
    if (stdout.includes('⚠️') || stdout.includes('不在注释列表')) {
      appStore.notify(`@${handle} 未在已移除列表中`, 'error')
    } else if (result.ok) {
      appStore.notify(`已恢复 @${handle}`, 'success')
      await loadAccounts()
    } else {
      appStore.notify('恢复失败: ' + (result.stderr || '未知错误'), 'error')
    }
  } catch (e) {
    appStore.notify('恢复失败: ' + e.message, 'error')
  } finally {
    restoring.value = null
  }
}

async function handleFollowingSync() {
  if (syncingFollowing.value) return

  syncingFollowing.value = true
  try {
    const result = await api.syncFollowingWithRadar()
    if (!result.ok) {
      appStore.notify('Following 同步失败: ' + (result.error || result.stderr || '未知错误'), 'error', 10000)
      return
    }

    const summary = result.summary || {}
    const xlsxPath = result.xlsx_report || summary.xlsx_report || 'xinfo/log/myfollowing.xlsx'
    const jsonPath = result.json_snapshot || summary.json_snapshot || ''
    const status = summary.completion_status || (summary.complete ? 'complete' : 'unknown')
    const countText = summary.expected_following_count
      ? `${summary.collected_following_count || 0}/${summary.expected_following_count}`
      : `${summary.collected_following_count || 0}`
    const suffix = jsonPath ? `；JSON: ${jsonPath}` : ''
    appStore.notify(
      `Following 同步完成(${status}, ${countText})：${xlsxPath}${suffix}`,
      status === 'complete' ? 'success' : 'info',
      15000,
    )
  } catch (e) {
    appStore.notify('Following 同步失败: ' + e.message, 'error', 10000)
  } finally {
    syncingFollowing.value = false
  }
}

async function handleAdd() {
  if (!canSubmitAdd.value || addSubmitting.value) return
  
  addSubmitting.value = true
  try {
    const handle = addForm.handle.trim()
    const note = addForm.note.trim()
    
    const result = await api.addRadarAccount(handle, note)
    
    const stdout = result.stdout || ''
    if (stdout.includes('⚠️') || stdout.includes('已在活跃列表')) {
      appStore.notify(`@${handle} 已在监控列表中`, 'error')
    } else if (stdout.includes('请用 restore')) {
      appStore.notify(`@${handle} 已移除，请使用恢复功能`, 'error')
    } else if (result.ok) {
      appStore.notify(`已添加 @${handle}`, 'success')
      closeAddDialog()
      await loadAccounts()
    } else {
      appStore.notify('添加失败: ' + (result.stderr || '未知错误'), 'error')
    }
  } catch (e) {
    appStore.notify('添加失败: ' + e.message, 'error')
  } finally {
    addSubmitting.value = false
  }
}

function closeAddDialog() {
  showAddDialog.value = false
  addForm.handle = ''
  addForm.note = ''
}

// Auto-focus handle input when dialog opens
watch(() => showAddDialog.value, async (show) => {
  if (show) {
    await nextTick()
    handleInput.value?.focus()
  }
})

onMounted(() => {
  loadAccounts()
})

onActivated(() => {
  // 页面激活时重新加载账号列表（从其他页面切换回来时）
  loadAccounts()
})
</script>

<script>
import { watch } from 'vue'
export default {
  name: 'AccountsPage'
}
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
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

.accounts-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  max-width: 400px;
}

.search-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-tertiary);
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

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.accounts-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.accounts-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.count-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.language-summary-badge {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.1);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.accounts-table {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  min-height: 200px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-tertiary);
  text-align: center;
}

.empty-icon {
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 13px;
  margin: 0;
}

.account-list {
  display: flex;
  flex-direction: column;
}

.account-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  transition: background var(--transition-fast);
}

.account-item:last-child {
  border-bottom: none;
}

.account-item:hover {
  background: var(--bg-hover);
}

.account-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.account-handle {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.language-badge {
  width: 30px;
  min-width: 30px;
  text-align: center;
  font-size: 10px;
  font-weight: 700;
  line-height: 18px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}

.language-badge-en {
  color: #1d4ed8;
  background: rgba(37, 99, 235, 0.1);
}

.language-badge-cn {
  color: #b45309;
  background: rgba(245, 158, 11, 0.14);
}

.language-badge-unknown {
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
}

.account-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.status-active {
  color: var(--accent-green);
  background: rgba(16, 185, 129, 0.1);
}

.status-removed {
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
}

.btn-danger {
  color: #ffffff;
  background: #ef4444;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
  color: #ffffff;
}

/* Dialog */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.dialog {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 90%;
  max-width: 480px;
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.dialog-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.dialog-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.dialog-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.dialog-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.form-input {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-blue);
  background: var(--bg-primary);
}

.input-with-prefix {
  display: flex;
  align-items: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.input-with-prefix:focus-within {
  border-color: var(--accent-blue);
  background: var(--bg-primary);
}

.input-prefix {
  padding: 8px 0 8px 12px;
  font-size: 13px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.input-with-prefix .form-input {
  border: none;
  padding-left: 0;
  background: transparent;
}

.input-with-prefix .form-input:focus {
  border: none;
  background: transparent;
}

.form-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin: 0;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
}
</style>
