<template>
  <div class="markdown-preview">
    <div class="preview-content" v-html="renderedHtml"></div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

// 配置 marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.error('Highlight error:', err)
      }
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true
})

// 渲染 Markdown
const renderedHtml = computed(() => {
  if (!props.content) {
    return '<p class="empty-hint">暂无内容</p>'
  }
  
  try {
    return marked.parse(props.content)
  } catch (err) {
    console.error('Markdown parse error:', err)
    return '<p class="error-hint">Markdown 解析失败</p>'
  }
})
</script>

<style scoped>
.markdown-preview {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.preview-content {
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.7;
}

/* Markdown 样式 */
.preview-content :deep(h1) {
  font-size: 28px;
  font-weight: 700;
  margin: 24px 0 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border-default);
  color: var(--text-primary);
}

.preview-content :deep(h2) {
  font-size: 24px;
  font-weight: 600;
  margin: 20px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.preview-content :deep(h3) {
  font-size: 20px;
  font-weight: 600;
  margin: 16px 0 10px;
  color: var(--text-primary);
}

.preview-content :deep(h4),
.preview-content :deep(h5),
.preview-content :deep(h6) {
  font-size: 16px;
  font-weight: 600;
  margin: 14px 0 8px;
  color: var(--text-primary);
}

.preview-content :deep(p) {
  margin: 12px 0;
  color: var(--text-secondary);
}

.preview-content :deep(ul),
.preview-content :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
  color: var(--text-secondary);
}

.preview-content :deep(li) {
  margin: 6px 0;
}

.preview-content :deep(code) {
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  color: var(--accent-coral);
}

.preview-content :deep(pre) {
  margin: 16px 0;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
}

.preview-content :deep(pre code) {
  padding: 0;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
}

.preview-content :deep(blockquote) {
  margin: 16px 0;
  padding: 12px 16px;
  border-left: 4px solid var(--accent-blue);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}

.preview-content :deep(a) {
  color: var(--accent-blue);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.preview-content :deep(a:hover) {
  color: var(--accent-coral);
  text-decoration: underline;
}

.preview-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
  margin: 16px 0;
}

.preview-content :deep(table) {
  width: 100%;
  margin: 16px 0;
  border-collapse: collapse;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.preview-content :deep(th),
.preview-content :deep(td) {
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  text-align: left;
}

.preview-content :deep(th) {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-primary);
}

.preview-content :deep(td) {
  color: var(--text-secondary);
}

.preview-content :deep(hr) {
  margin: 24px 0;
  border: none;
  border-top: 2px solid var(--border-subtle);
}

.empty-hint,
.error-hint {
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 40px 20px;
}

.error-hint {
  color: var(--accent-coral);
}
</style>
