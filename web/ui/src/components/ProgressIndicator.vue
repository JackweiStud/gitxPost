<template>
  <transition name="fade">
    <div v-if="visible" class="progress-indicator">
      <div class="progress-header">
        <span class="progress-title">{{ currentStepTitle }}</span>
        <span class="progress-percent">{{ progress }}%</span>
      </div>
      
      <div class="progress-bar-container">
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: progress + '%' }"
            :class="{ 'progress-complete': progress >= 100 }"
          ></div>
        </div>
      </div>
      
      <div class="progress-message">{{ statusMessage }}</div>
      
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
  // 是否显示进度指示器
  visible: {
    type: Boolean,
    default: false
  },
  // 当前步骤：idle | outline | content | complete | error
  currentStep: {
    type: String,
    default: 'idle',
    validator: (value) => ['idle', 'outline', 'content', 'complete', 'error'].includes(value)
  },
  // 进度百分比 (0-100)
  progress: {
    type: Number,
    default: 0,
    validator: (value) => value >= 0 && value <= 100
  },
  // 是否可以取消
  canCancel: {
    type: Boolean,
    default: false
  },
  // 自定义状态消息（可选）
  customMessage: {
    type: String,
    default: ''
  }
})

defineEmits(['cancel'])

// 当前步骤标题
const currentStepTitle = computed(() => {
  const titles = {
    idle: '准备中',
    outline: '生成骨架',
    content: '生成全文',
    complete: '完成',
    error: '错误'
  }
  return titles[props.currentStep] || '处理中'
})

// 状态消息
const statusMessage = computed(() => {
  // 如果有自定义消息，优先使用
  if (props.customMessage) {
    return props.customMessage
  }
  
  // 根据步骤和进度生成默认消息
  if (props.currentStep === 'outline') {
    if (props.progress < 30) {
      return '正在分析主题...'
    } else if (props.progress < 70) {
      return '正在生成大纲...'
    } else {
      return '正在优化结构...'
    }
  } else if (props.currentStep === 'content') {
    // 根据进度估算章节
    const totalSections = 5
    const currentSection = Math.min(
      Math.floor(((props.progress - 50) / 50) * totalSections) + 1,
      totalSections
    )
    return `正在扩展第 ${currentSection}/${totalSections} 章节...`
  } else if (props.currentStep === 'complete') {
    return '生成完成！'
  } else if (props.currentStep === 'error') {
    return '生成失败，请重试'
  }
  
  return '正在处理...'
})
</script>

<style scoped>
.progress-indicator {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  margin: 16px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: #3b82f6;
  font-variant-numeric: tabular-nums;
}

.progress-bar-container {
  margin-bottom: 12px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  border-radius: 4px;
  transition: width 0.3s ease-out;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 2s infinite;
}

.progress-fill.progress-complete {
  background: linear-gradient(90deg, #10b981, #059669);
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-message {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 12px;
  min-height: 20px;
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

/* 淡入淡出动画 */
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

/* 响应式设计 */
@media (max-width: 768px) {
  .progress-indicator {
    padding: 16px;
    margin: 12px 0;
  }
  
  .progress-title {
    font-size: 15px;
  }
  
  .progress-percent {
    font-size: 13px;
  }
  
  .progress-message {
    font-size: 13px;
  }
}
</style>
