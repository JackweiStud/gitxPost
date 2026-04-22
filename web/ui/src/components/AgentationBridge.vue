<template>
  <div class="agentation-bridge">
    <div ref="mountRef"></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import React from 'react'
import { createRoot } from 'react-dom/client'
import { Agentation, loadAnnotations, saveAnnotations } from 'agentation'
import { useAppStore } from '../stores/app.js'

const props = defineProps({
  articleId: {
    type: String,
    default: ''
  },
  annotations: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['change'])

const mountRef = ref(null)
const appStore = useAppStore()
let root = null

const normalizeAnnotation = (annotation) => ({
  id: annotation.id,
  x: annotation.x,
  y: annotation.y,
  comment: annotation.comment || '',
  element: annotation.element || '',
  elementPath: annotation.elementPath || '',
  timestamp: annotation.timestamp || Date.now(),
  selectedText: annotation.selectedText || '',
  boundingBox: annotation.boundingBox || null,
  nearbyText: annotation.nearbyText || '',
  cssClasses: annotation.cssClasses || '',
  nearbyElements: annotation.nearbyElements || '',
  computedStyles: annotation.computedStyles || null,
  fullPath: annotation.fullPath || '',
  accessibility: annotation.accessibility || '',
  isMultiSelect: Boolean(annotation.isMultiSelect),
  isFixed: Boolean(annotation.isFixed)
})

const getPathname = () => {
  if (props.articleId) {
    return `/articles/${props.articleId}/agentation`
  }

  if (typeof window !== 'undefined') {
    return window.location.pathname || '/'
  }

  return '/'
}

const syncAnnotationsToStorage = (annotations) => {
  saveAnnotations(getPathname(), (annotations || []).map(normalizeAnnotation))
}

const emitCurrentAnnotations = () => {
  emit('change', loadAnnotations(getPathname()).map(normalizeAnnotation))
}

const handleCopy = () => {
  emitCurrentAnnotations()
  appStore.notify('Agentation 已复制到剪贴板', 'success', 2500)
}

const renderToolbar = () => {
  if (!mountRef.value || root) return

  root = createRoot(mountRef.value)
  root.render(
    React.createElement(Agentation, {
      onAnnotationAdd: emitCurrentAnnotations,
      onAnnotationDelete: emitCurrentAnnotations,
      onAnnotationUpdate: emitCurrentAnnotations,
      onAnnotationsClear: emitCurrentAnnotations,
      onCopy: handleCopy
    })
  )
}

watch(
  () => props.annotations,
  (annotations) => {
    syncAnnotationsToStorage(annotations)
  },
  { deep: true, immediate: true }
)

onMounted(() => {
  renderToolbar()
})

onBeforeUnmount(() => {
  if (root) {
    root.unmount()
    root = null
  }
})
</script>

<style scoped>
.agentation-bridge {
  position: relative;
  z-index: 30;
}
</style>
