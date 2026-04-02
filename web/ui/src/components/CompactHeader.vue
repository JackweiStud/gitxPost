<template>
  <div class="compact-header">
    <button class="btn-back" @click="goBack" title="返回文章列表">
      ← 返回
    </button>
    
    <input 
      ref="titleInputRef"
      v-model="localTitle" 
      class="title-input" 
      @blur="saveTitle"
      @keydown.enter="$event.target.blur()"
      placeholder="输入文章标题..."
    />
    
    <select 
      v-model="localStyle" 
      class="style-selector" 
      @change="onStyleChange"
      :disabled="isGenerating"
      title="选择文章风格"
    >
      <option value="zara">Zara 风格</option>
      <option value="tech">技术风格</option>
      <option value="fun">趣味风格</option>
    </select>
    
    <div class="header-badges">
      <span class="step-badge" :class="`step-${step}`">
        {{ stepLabel }}
      </span>
      <span class="status-badge" :class="`status-${status}`">
        {{ statusLabel }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  articleId: {
    type: String,
    required: true
  },
  title: {
    type: String,
    default: ''
  },
  style: {
    type: String,
    default: 'zara',
    validator: (value) => ['zara', 'tech', 'fun'].includes(value)
  },
  step: {
    type: String,
    default: 'title',
    validator: (value) => ['title', 'outline', 'content', 'preview'].includes(value)
  },
    status: {
      type: String,
      default: 'draft',
      validator: (value) => ['draft', 'published'].includes(value)
    },
    focusTitle: {
      type: Boolean,
      default: false
    },
    isGenerating: {
      type: Boolean,
      default: false
    }
  })

const emit = defineEmits(['update:title', 'update:style', 'save'])

const router = useRouter()
const localTitle = ref(props.title)
const localStyle = ref(props.style)
const titleInputRef = ref(null)

// 步骤标签映射
const stepLabel = computed(() => {
  const labels = {
    title: '标题',
    outline: '骨架',
    content: '内容',
    preview: '预览'
  }
  return labels[props.step] || '标题'
})

// 状态标签映射
const statusLabel = computed(() => {
  if (props.isGenerating) return '生成中'
  const labels = {
    draft: '草稿',
    published: '已发布'
  }
  return labels[props.status] || '草稿'
})

// 监听 props 变化
watch(() => props.title, (newTitle) => {
  localTitle.value = newTitle
})

watch(() => props.style, (newStyle) => {
  localStyle.value = newStyle
})

const focusTitleInput = async () => {
  if (!props.focusTitle) return

  await nextTick()
  const input = titleInputRef.value
  if (input) {
    input.focus()
    if (typeof input.select === 'function') {
      input.select()
    }
  }
}

watch(() => props.focusTitle, (value) => {
  if (value) {
    focusTitleInput()
  }
})

// 保存标题
const saveTitle = async () => {
  if (localTitle.value === props.title) return
  
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${props.articleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: localTitle.value })
    })
    
    const data = await response.json()
    
    if (data.ok) {
      emit('update:title', localTitle.value)
      emit('save', { field: 'title', value: localTitle.value })
    }
  } catch (error) {
    console.error('Failed to save title:', error)
  }
}

// 风格变化处理
const onStyleChange = async () => {
  // 保存到 localStorage
  localStorage.setItem('article_preferred_style', localStyle.value)
  
  // 保存到文章元数据
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${props.articleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: localStyle.value })
    })
    
    const data = await response.json()
    
    if (data.ok) {
      emit('update:style', localStyle.value)
      emit('save', { field: 'style', value: localStyle.value })
    }
  } catch (error) {
    console.error('Failed to save style:', error)
  }
}

// 返回文章列表
const goBack = () => {
  router.push('/articles')
}

// 组件挂载时从 localStorage 读取上次选择的风格
onMounted(() => {
  const savedStyle = localStorage.getItem('article_preferred_style')
  if (savedStyle && ['zara', 'tech', 'fun'].includes(savedStyle) && !props.style) {
    localStyle.value = savedStyle
  }

  focusTitleInput()
})
</script>

<style scoped>
.compact-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  height: 60px;
  box-sizing: border-box;
}

.btn-back {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-back:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #374151;
}

.title-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  outline: none;
  transition: border-color 0.2s;
  min-width: 200px;
}

.title-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.title-input::placeholder {
  color: #9ca3af;
  font-weight: normal;
}

.style-selector {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
  min-width: 120px;
}

.style-selector:hover:not(:disabled) {
  border-color: #9ca3af;
}

.style-selector:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.style-selector:disabled {
  background: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.header-badges {
  display: flex;
  gap: 8px;
  align-items: center;
}

.step-badge,
.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.step-badge {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.step-badge.step-outline {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.step-badge.step-content {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.step-badge.step-preview {
  background: #e0e7ff;
  color: #3730a3;
  border: 1px solid #c7d2fe;
}

.status-badge {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #d1d5db;
}

.status-badge.status-published {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .compact-header {
    flex-wrap: wrap;
    height: auto;
    min-height: 60px;
  }
  
  .title-input {
    order: 1;
    flex-basis: 100%;
  }
  
  .btn-back {
    order: 2;
  }
  
  .style-selector {
    order: 3;
  }
  
  .header-badges {
    order: 4;
    margin-left: auto;
  }
}
</style>
