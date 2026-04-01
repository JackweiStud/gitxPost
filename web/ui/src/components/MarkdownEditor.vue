<template>
  <div class="markdown-editor">
    <!-- 工具栏 -->
    <div class="editor-toolbar">
      <button 
        class="toolbar-btn" 
        type="button"
        @click="triggerImageUpload"
        title="插入图片"
        :disabled="readonly || !articleId"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
        插入图片
      </button>
      
      <!-- 上传进度提示 -->
      <span v-if="uploadingImage" class="upload-status">
        上传中... {{ uploadProgress }}%
      </span>
    </div>
    
    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp"
      @change="handleFileSelect"
      class="file-input-hidden"
    />
    
    <textarea
      ref="textareaRef"
      v-model="localContent"
      @input="handleInput"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @paste="handlePaste"
      :placeholder="placeholder"
      :readonly="readonly"
      class="editor-textarea"
    ></textarea>
  </div>
</template>

<script setup>
import { nextTick, ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '在此输入 Markdown 内容...'
  },
  readonly: {
    type: Boolean,
    default: false
  },
  // 文章 ID（用于自动保存）
  articleId: {
    type: String,
    default: null
  },
  // 是否启用自动保存
  autoSave: {
    type: Boolean,
    default: true
  },
  // 自动保存延迟（毫秒）
  autoSaveDelay: {
    type: Number,
    default: 3000
  }
})

const emit = defineEmits(['update:modelValue', 'save-status'])

const textareaRef = ref(null)
const fileInputRef = ref(null)
const localContent = ref(props.modelValue)
const saveStatus = ref('saved') // 'saved' | 'saving' | 'unsaved' | 'error'
const lastSaved = ref(null)
const uploadingImage = ref(false)
const uploadProgress = ref(0)
let autoSaveTimer = null

// 监听外部变化
watch(() => props.modelValue, (newValue) => {
  if (newValue !== localContent.value) {
    localContent.value = newValue
  }
})

// 处理输入
const handleInput = () => {
  emit('update:modelValue', localContent.value)
  
  // 触发自动保存
  if (props.autoSave && props.articleId) {
    saveStatus.value = 'unsaved'
    emit('save-status', { status: 'unsaved', lastSaved: lastSaved.value })
    
    // 清除之前的定时器
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
    }
    
    // 设置新的定时器（3秒后保存）
    autoSaveTimer = setTimeout(() => {
      performAutoSave()
    }, props.autoSaveDelay)
  }
}

// 执行自动保存
const performAutoSave = async () => {
  if (!props.articleId || props.readonly) return
  
  try {
    saveStatus.value = 'saving'
    emit('save-status', { status: 'saving', lastSaved: lastSaved.value })
    
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${props.articleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: localContent.value })
    })
    
    const data = await response.json()
    
    if (data.ok) {
      saveStatus.value = 'saved'
      lastSaved.value = new Date()
      emit('save-status', { status: 'saved', lastSaved: lastSaved.value })
    } else {
      throw new Error(data.error || 'Save failed')
    }
  } catch (error) {
    console.error('Auto-save failed:', error)
    saveStatus.value = 'error'
    emit('save-status', { status: 'error', lastSaved: lastSaved.value })
  }
}

// 手动保存（供父组件调用）
const save = async () => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    autoSaveTimer = null
  }
  await performAutoSave()
}

// 触发图片上传
const triggerImageUpload = async () => {
  if (props.readonly || !props.articleId || uploadingImage.value) return

  await nextTick()
  const input = fileInputRef.value
  if (!input) return

  if (typeof input.showPicker === 'function') {
    try {
      input.showPicker()
      return
    } catch (error) {
      console.warn('showPicker failed, falling back to click()', error)
    }
  }

  input.click()
}

// 处理文件选择
const handleFileSelect = async (event) => {
  const files = event.target.files
  if (files && files.length > 0) {
    await uploadImage(files[0])
  }
  // 清空 input，允许重复选择同一文件
  event.target.value = ''
}

// 处理拖拽
const handleDragOver = (event) => {
  event.preventDefault()
  event.stopPropagation()
}

const handleDrop = async (event) => {
  event.preventDefault()
  event.stopPropagation()
  
  if (props.readonly || !props.articleId) return
  
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    if (file.type.startsWith('image/')) {
      await uploadImage(file)
    }
  }
}

// 处理粘贴
const handlePaste = async (event) => {
  if (props.readonly || !props.articleId) return
  
  const items = event.clipboardData?.items
  if (!items) return
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await uploadImage(file)
      }
      break
    }
  }
}

// 上传图片
const uploadImage = async (file) => {
  if (!props.articleId) {
    console.error('Cannot upload image: articleId is required')
    return
  }
  
  // 验证文件类型
  const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
  if (!validTypes.includes(file.type)) {
    alert('仅支持 PNG、JPG、GIF、WebP 格式的图片')
    return
  }
  
  // 验证文件大小（最大 10MB）
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    alert('图片大小不能超过 10MB')
    return
  }
  
  try {
    uploadingImage.value = true
    uploadProgress.value = 0
    
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${props.articleId}/images`, {
      method: 'POST',
      body: formData
    })
    
    uploadProgress.value = 100
    
    const data = await response.json()
    
    if (data.ok && data.markdown) {
      // 在光标位置插入 markdown 语法
      insertTextAtCursor(data.markdown)
    } else {
      throw new Error(data.error || 'Upload failed')
    }
  } catch (error) {
    console.error('Image upload failed:', error)
    alert('图片上传失败：' + error.message)
  } finally {
    uploadingImage.value = false
    uploadProgress.value = 0
  }
}

// 在光标位置插入文本
const insertTextAtCursor = (text) => {
  const textarea = textareaRef.value
  if (!textarea) return
  
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const before = localContent.value.substring(0, start)
  const after = localContent.value.substring(end)
  
  // 插入文本，前后加换行
  const newText = before + '\n' + text + '\n' + after
  localContent.value = newText
  
  // 触发更新
  emit('update:modelValue', localContent.value)
  
  // 设置新的光标位置
  setTimeout(() => {
    const newPosition = start + text.length + 2
    textarea.setSelectionRange(newPosition, newPosition)
    textarea.focus()
  }, 0)
  
  // 触发自动保存
  if (props.autoSave && props.articleId) {
    saveStatus.value = 'unsaved'
    emit('save-status', { status: 'unsaved', lastSaved: lastSaved.value })
    
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
    }
    
    autoSaveTimer = setTimeout(() => {
      performAutoSave()
    }, props.autoSaveDelay)
  }
}

// 清理定时器
onUnmounted(() => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
})

// 暴露方法供父组件调用
defineExpose({
  focus: () => {
    textareaRef.value?.focus()
  },
  save,
  saveStatus,
  lastSaved
})
</script>

<style scoped>
.markdown-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary, #f9fafb);
  border: 1px solid var(--border-default, #e5e7eb);
  border-bottom: none;
  border-radius: var(--radius-md, 8px) var(--radius-md, 8px) 0 0;
}

.file-input-hidden {
  position: absolute;
  left: -9999px;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: white;
  border: 1px solid var(--border-default, #d1d5db);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  transition: all 0.2s;
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--bg-tertiary, #f3f4f6);
  border-color: var(--border-hover, #9ca3af);
  color: var(--text-primary, #111827);
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toolbar-btn svg {
  flex-shrink: 0;
}

.upload-status {
  font-size: 13px;
  color: var(--accent-blue, #3b82f6);
  margin-left: auto;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  padding: 16px;
  border: 1px solid var(--border-default, #e5e7eb);
  border-radius: 0 0 var(--radius-md, 8px) var(--radius-md, 8px);
  background: var(--bg-primary, white);
  color: var(--text-primary, #111827);
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
  transition: border-color var(--transition-fast, 0.2s);
}

.editor-textarea:focus {
  border-color: var(--accent-blue, #3b82f6);
}

.editor-textarea[readonly] {
  background: var(--bg-secondary, #f9fafb);
  cursor: not-allowed;
}

.editor-textarea::placeholder {
  color: var(--text-tertiary, #9ca3af);
}
</style>
