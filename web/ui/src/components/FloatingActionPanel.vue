<template>
  <div class="floating-panel">
    <div class="save-status" :class="`status-${saveStatus}`">
      <span class="status-icon">{{ statusIcon }}</span>
      <span class="status-text">{{ statusText }}</span>
    </div>
    
    <div class="action-buttons">
      <!-- 一键生成按钮 -->
      <button 
        v-if="canGenerate" 
        class="btn-primary btn-large"
        @click="$emit('generate')"
        :disabled="isGenerating"
      >
        <span v-if="isGenerating">生成中...</span>
        <span v-else>一键生成</span>
      </button>
      
      <!-- 发布文章按钮 -->
      <button 
        v-if="canPublish" 
        class="btn-success btn-large"
        @click="$emit('publish')"
        :disabled="isPublishing"
      >
        <span v-if="isPublishing">发布中...</span>
        <span v-else>发布文章</span>
      </button>
      
      <!-- 预览切换按钮 -->
      <button 
        class="btn-icon" 
        @click="$emit('toggle-preview')"
        title="切换预览"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 保存状态：saved | saving | unsaved | error
  saveStatus: {
    type: String,
    default: 'saved',
    validator: (value) => ['saved', 'saving', 'unsaved', 'error'].includes(value)
  },
  // 最后保存时间
  lastSaved: {
    type: Date,
    default: null
  },
  // 文章步骤：title | outline | content | preview
  step: {
    type: String,
    default: 'title',
    validator: (value) => ['title', 'outline', 'content', 'preview'].includes(value)
  },
  // 是否正在生成
  isGenerating: {
    type: Boolean,
    default: false
  },
  // 是否正在发布
  isPublishing: {
    type: Boolean,
    default: false
  },
  // 文章状态
  status: {
    type: String,
    default: 'draft',
    validator: (value) => ['draft', 'published'].includes(value)
  }
})

defineEmits(['generate', 'publish', 'toggle-preview'])

// 是否可以生成（标题步骤或骨架步骤）
const canGenerate = computed(() => {
  return ['title', 'outline'].includes(props.step) && 
         props.status !== 'published' && 
         !props.isGenerating
})

// 是否可以发布（内容步骤或预览步骤）
const canPublish = computed(() => {
  return ['content', 'preview'].includes(props.step) && 
         props.status !== 'published' && 
         !props.isPublishing
})

// 状态图标
const statusIcon = computed(() => {
  const icons = {
    saved: '✓',
    saving: '⟳',
    unsaved: '•',
    error: '⚠'
  }
  return icons[props.saveStatus] || '•'
})

// 状态文本
const statusText = computed(() => {
  if (props.saveStatus === 'saved' && props.lastSaved) {
    const time = props.lastSaved.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
    return `已保存 ${time}`
  }
  
  const texts = {
    saved: '已保存',
    saving: '保存中...',
    unsaved: '未保存',
    error: '保存失败'
  }
  return texts[props.saveStatus] || '未保存'
})
</script>

<style scoped>
.floating-panel {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 1000;
  min-width: 200px;
}

.save-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 6px;
  transition: all 0.2s;
}

.status-icon {
  font-size: 14px;
  font-weight: bold;
}

.status-saved {
  background: #d1fae5;
  color: #065f46;
}

.status-saved .status-icon {
  color: #10b981;
}

.status-saving {
  background: #dbeafe;
  color: #1e40af;
}

.status-saving .status-icon {
  animation: spin 1s linear infinite;
}

.status-unsaved {
  background: #fef3c7;
  color: #92400e;
}

.status-unsaved .status-icon {
  color: #f59e0b;
}

.status-error {
  background: #fee2e2;
  color: #991b1b;
}

.status-error .status-icon {
  color: #ef4444;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-large {
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-large:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-success {
  background: #10b981;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
}

.btn-success:active:not(:disabled) {
  transform: translateY(0);
}

.btn-icon {
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.btn-icon:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #374151;
  transform: translateY(-1px);
}

.btn-icon:active {
  transform: translateY(0);
}

.btn-icon svg {
  display: block;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .floating-panel {
    bottom: 16px;
    right: 16px;
    left: 16px;
    min-width: auto;
  }
  
  .action-buttons {
    flex-direction: row;
  }
  
  .btn-large {
    flex: 1;
  }
  
  .btn-icon {
    flex-shrink: 0;
  }
}

/* 打印时隐藏 */
@media print {
  .floating-panel {
    display: none;
  }
}
</style>
