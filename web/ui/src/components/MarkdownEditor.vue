<template>
  <div class="markdown-editor">
    <textarea
      ref="textareaRef"
      v-model="localContent"
      @input="handleInput"
      :placeholder="placeholder"
      :readonly="readonly"
      class="editor-textarea"
    ></textarea>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

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
  }
})

const emit = defineEmits(['update:modelValue'])

const textareaRef = ref(null)
const localContent = ref(props.modelValue)

// 监听外部变化
watch(() => props.modelValue, (newValue) => {
  if (newValue !== localContent.value) {
    localContent.value = newValue
  }
})

// 处理输入
const handleInput = () => {
  emit('update:modelValue', localContent.value)
}

// 暴露方法供父组件调用
defineExpose({
  focus: () => {
    textareaRef.value?.focus()
  }
})
</script>

<style scoped>
.markdown-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
  transition: border-color var(--transition-fast);
}

.editor-textarea:focus {
  border-color: var(--accent-blue);
}

.editor-textarea:readonly {
  background: var(--bg-secondary);
  cursor: not-allowed;
}

.editor-textarea::placeholder {
  color: var(--text-tertiary);
}
</style>
