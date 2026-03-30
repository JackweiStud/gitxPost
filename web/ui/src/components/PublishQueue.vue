<template>
  <div class="card publish-queue-card">
    <div class="card-header">
      <h3>发布队列</h3>
      <span v-if="scheduledCount > 0" class="badge badge-amber">
        排队中 {{ scheduledCount }} 条
      </span>
    </div>

    <div v-if="queue.length === 0" class="empty-state">
      <svg class="empty-icon" width="80" height="80" viewBox="0 0 80 80" fill="none">
        <circle cx="40" cy="40" r="38" stroke="currentColor" stroke-width="2" stroke-dasharray="4 4" opacity="0.2"/>
        <path d="M40 25v30M25 40h30" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" opacity="0.3"/>
      </svg>
      <p class="empty-title">还没有发布任务</p>
      <p class="empty-hint">发布的内容会显示在这里</p>
    </div>

    <div v-else class="queue-list">
      <div
        v-for="task in queue"
        :key="task.id"
        class="queue-item"
        :class="'status-' + task.status"
      >
        <div class="queue-status">
          <span class="status-badge" :class="getStatusClass(task.status)">
            {{ getStatusText(task.status) }}
          </span>
        </div>
        <div class="queue-type">
          <span class="type-badge">{{ task.type === 'post' ? 'Post' : 'Article' }}</span>
        </div>
        <div class="queue-content">
          <div class="content-text">{{ getContentPreview(task) }}</div>
          <div class="content-meta">
            <span v-if="task.status === 'scheduled'" class="meta-scheduled">
              预期 {{ formatTime(task.scheduled_at) }}
            </span>
            <span v-else class="meta-time">{{ formatTime(task.created_at) }}</span>
            <span v-if="task.executed_at" class="meta-executed">
              · 执行于 {{ formatTime(task.executed_at) }}
            </span>
          </div>
        </div>
        <div class="queue-actions">
          <button
            v-if="task.status === 'scheduled'"
            class="btn-icon"
            @click="$emit('cancel', task.id)"
            title="取消"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <button
            v-if="task.status === 'failed'"
            class="btn-icon"
            @click="$emit('retry', task.id)"
            title="重试"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
          </button>
          <button
            class="btn-icon"
            @click="$emit('delete', task.id)"
            title="删除"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  queue: {
    type: Array,
    default: () => []
  }
})

defineEmits(['cancel', 'retry', 'delete'])

const scheduledCount = computed(() => {
  return props.queue.filter(t => t.status === 'scheduled').length
})

function getStatusClass(status) {
  const map = {
    scheduled: 'badge-amber',
    running: 'badge-blue',
    done: 'badge-green',
    failed: 'badge-red',
    cancelled: 'badge-gray'
  }
  return map[status] || 'badge-gray'
}

function getStatusText(status) {
  const map = {
    scheduled: '● 排队中',
    running: '● 执行中',
    done: '✓ 已完成',
    failed: '✗ 失败',
    cancelled: '○ 已取消'
  }
  return map[status] || status
}

function getContentPreview(task) {
  if (task.type === 'post') {
    const text = task.content?.text || ''
    return text.length > 50 ? text.substring(0, 50) + '...' : text
  } else if (task.type === 'article') {
    return task.content?.md_path || '文章'
  }
  return ''
}

function formatTime(isoString) {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    const now = new Date()
    const diff = now - date
    
    // 如果是未来时间
    if (diff < 0) {
      const absDiff = Math.abs(diff)
      const minutes = Math.floor(absDiff / 60000)
      const hours = Math.floor(minutes / 60)
      const days = Math.floor(hours / 24)
      
      if (days > 0) return `${days} 天后`
      if (hours > 0) return `${hours} 小时后`
      if (minutes > 0) return `${minutes} 分钟后`
      return '即将执行'
    }
    
    // 过去时间
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    
    if (days > 0) return `${days} 天前`
    if (hours > 0) return `${hours} 小时前`
    if (minutes > 0) return `${minutes} 分钟前`
    return '刚刚'
  } catch (e) {
    return isoString
  }
}
</script>

<style scoped>
.publish-queue-card {
  margin-top: 24px;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.queue-item {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.queue-item:hover {
  background: var(--bg-hover);
}

.queue-status {
  display: flex;
  align-items: center;
}

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.badge-amber {
  background: var(--accent-amber-dim);
  color: var(--accent-amber);
}

.badge-blue {
  background: rgba(59, 130, 246, 0.12);
  color: var(--accent-blue);
}

.badge-green {
  background: var(--accent-green-dim);
  color: var(--accent-green);
}

.badge-red {
  background: var(--accent-red-dim);
  color: var(--accent-red);
}

.badge-gray {
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}

.queue-type {
  display: flex;
  align-items: center;
}

.type-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.queue-content {
  min-width: 0;
}

.content-text {
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.meta-time {
  font-variant-numeric: tabular-nums;
}

.meta-scheduled {
  font-variant-numeric: tabular-nums;
  color: var(--accent-amber);
  font-weight: 600;
}

.meta-executed {
  opacity: 0.7;
}

.queue-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.queue-item:hover .queue-actions {
  opacity: 1;
}

.btn-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  padding: 0;
}

.btn-icon:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.empty-state {
  text-align: center;
  padding: 40px 16px;
  color: var(--text-tertiary);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-icon {
  color: var(--text-tertiary);
  margin-bottom: 16px;
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 4px 0;
}

.empty-hint {
  font-size: 12px;
  margin: 0;
  opacity: 0.8;
}
</style>
