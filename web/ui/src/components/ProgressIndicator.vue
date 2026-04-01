<template>
  <transition name="fade">
    <div v-if="visible" class="progress-indicator">
      <div class="progress-header">
        <span class="progress-title">自动生成日志</span>
      </div>

      <div class="log-panel" role="log" aria-live="polite">
        <div
          v-for="(entry, index) in displayEntries"
          :key="entry.id"
          class="log-line"
          :class="entry.level"
        >
          <span class="log-prefix">{{ prefixByLevel[entry.level] || '•' }}</span>
          <span class="log-text">{{ formatEntryText(entry, index) }}</span>
        </div>
      </div>

      <button
        v-if="canCancel"
        class="btn-cancel"
        @click="$emit('cancel')"
      >
        取消
      </button>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  currentStep: {
    type: String,
    default: 'idle',
    validator: (value) => ['idle', 'outline', 'content', 'complete', 'error'].includes(value)
  },
  canCancel: {
    type: Boolean,
    default: false
  },
  pulse: {
    type: Number,
    default: 0
  },
  logEntries: {
    type: Array,
    default: () => []
  }
})

defineEmits(['cancel'])

const fallbackEntries = {
  idle: [{ id: 'idle', text: '等待用户点击一键生成', level: 'pending' }],
  outline: [{ id: 'outline', text: '正在整理文章骨架...', level: 'running' }],
  content: [{ id: 'content', text: '正在扩写正文...', level: 'running' }],
  complete: [{ id: 'complete', text: '正文已生成并同步回编辑器，可直接继续修改', level: 'done' }],
  error: [{ id: 'error', text: '生成失败，请查看错误提示', level: 'error' }]
}

const prefixByLevel = {
  running: '▶',
  done: '✓',
  error: '!',
  pending: '•',
  info: '•'
}

const displayEntries = computed(() => {
  if (props.logEntries && props.logEntries.length > 0) {
    return props.logEntries.map((entry, index) => ({
      id: entry.id || `${index}-${entry.text}`,
      text: entry.text,
      level: entry.level || 'info'
    }))
  }

  return fallbackEntries[props.currentStep] || fallbackEntries.idle
})

const liveEntryIndex = computed(() => {
  if (!props.logEntries || props.logEntries.length === 0) {
    return -1
  }

  for (let index = props.logEntries.length - 1; index >= 0; index--) {
    if ((props.logEntries[index].level || 'info') === 'running') {
      return index
    }
  }

  return -1
})

const formatEntryText = (entry, index) => {
  if (index === liveEntryIndex.value && entry.level === 'running') {
    const suffix = '.'.repeat((props.pulse % 3) + 1)
    return `${entry.text}${suffix}`
  }

  return entry.text
}
</script>

<style scoped>
.progress-indicator {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px 20px 20px;
  margin: 16px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.progress-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.progress-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  letter-spacing: 0.01em;
}

.log-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  margin-bottom: 14px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  max-height: 220px;
  overflow: auto;
}

.log-line {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.55;
  color: #475569;
}

.log-line.running {
  color: #1d4ed8;
  font-weight: 600;
}

.log-line.done {
  color: #16a34a;
}

.log-line.error {
  color: #dc2626;
}

.log-line.pending,
.log-line.info {
  color: #64748b;
}

.log-prefix {
  width: 16px;
  flex: 0 0 16px;
  text-align: center;
  font-weight: 700;
}

.log-text {
  flex: 1;
  word-break: break-word;
}

.btn-cancel {
  width: 100%;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #374151;
}

.btn-cancel:active {
  background: #e5e7eb;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (max-width: 768px) {
  .progress-indicator {
    padding: 16px;
    margin: 12px 0;
  }

  .progress-title {
    font-size: 14px;
  }

  .log-panel {
    padding: 12px 14px;
    max-height: 180px;
  }
}
</style>
