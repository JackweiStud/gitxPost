<template>
  <aside class="annotation-panel">
    <div class="annotation-panel__header">
      <div>
        <p class="annotation-panel__eyebrow">Agentation</p>
        <h3>修改标注</h3>
      </div>
      <span class="annotation-panel__count">{{ annotations.length }}</span>
    </div>

    <p class="annotation-panel__hint">
      在预览区优先点选要修改的位置，也可以补充标注编辑器里的文本。下面会汇总成可直接交给 UI/Agent 的结构化说明。
    </p>

    <div class="annotation-panel__actions">
      <button
        type="button"
        class="annotation-panel__button"
        :disabled="!annotations.length"
        @click="copySummary"
      >
        复制标注摘要
      </button>
    </div>

    <div v-if="annotations.length" class="annotation-panel__list">
      <article
        v-for="annotation in annotations"
        :key="annotation.id"
        class="annotation-card"
      >
        <div class="annotation-card__meta">
          <span class="annotation-card__element">{{ annotation.element || '未识别元素' }}</span>
          <span class="annotation-card__path">{{ annotation.elementPath || '无路径' }}</span>
        </div>
        <p v-if="annotation.selectedText" class="annotation-card__quote">
          “{{ annotation.selectedText }}”
        </p>
        <p class="annotation-card__comment">{{ annotation.comment }}</p>
      </article>
    </div>

    <div v-else class="annotation-panel__empty">
      还没有标注。点击页面里的元素后输入“这里要怎么改”，就会自动出现在这里。
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  annotations: {
    type: Array,
    default: () => []
  }
})

const summaryText = computed(() => {
  if (!props.annotations.length) {
    return '暂无标注'
  }

  return props.annotations.map((annotation, index) => {
    const lines = [
      `${index + 1}. 元素: ${annotation.element || '未识别元素'}`,
      `路径: ${annotation.elementPath || '无路径'}`,
      `说明: ${annotation.comment || '无说明'}`
    ]

    if (annotation.selectedText) {
      lines.push(`选中文本: ${annotation.selectedText}`)
    }

    if (annotation.nearbyText) {
      lines.push(`附近文本: ${annotation.nearbyText}`)
    }

    return lines.join('\n')
  }).join('\n\n')
})

const copySummary = async () => {
  try {
    await navigator.clipboard.writeText(summaryText.value)
  } catch (error) {
    console.error('Failed to copy annotation summary:', error)
  }
}
</script>

<style scoped>
.annotation-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border-default, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  background: linear-gradient(180deg, rgba(249, 250, 251, 0.96), rgba(255, 255, 255, 0.98));
}

.annotation-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.annotation-panel__eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-blue, #3b82f6);
}

.annotation-panel__header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary, #111827);
}

.annotation-panel__count {
  min-width: 32px;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--bg-secondary, #f3f4f6);
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary, #4b5563);
  text-align: center;
}

.annotation-panel__hint,
.annotation-panel__empty {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary, #6b7280);
}

.annotation-panel__actions {
  display: flex;
  justify-content: flex-start;
}

.annotation-panel__button {
  padding: 8px 12px;
  border: 1px solid var(--border-default, #d1d5db);
  border-radius: 8px;
  background: white;
  color: var(--text-primary, #111827);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.annotation-panel__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.annotation-panel__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 260px;
  overflow-y: auto;
}

.annotation-card {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--border-subtle, #e5e7eb);
}

.annotation-card__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.annotation-card__element {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #111827);
}

.annotation-card__path {
  font-size: 12px;
  color: var(--text-tertiary, #9ca3af);
  word-break: break-all;
}

.annotation-card__quote,
.annotation-card__comment {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.annotation-card__quote {
  margin-bottom: 6px;
  color: var(--text-secondary, #4b5563);
  font-style: italic;
}

.annotation-card__comment {
  color: var(--text-primary, #111827);
}
</style>
