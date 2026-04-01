import { ref, computed, onUnmounted, watch, unref } from 'vue'

/**
 * Workflow Orchestrator Composable
 *
 * Manages the one-click auto-generation workflow for articles.
 * Handles state management, API calls, and WebSocket event listening.
 *
 * Requirements: FR-1.1, FR-1.1.1, AC-1
 */
export function useWorkflowOrchestrator(articleIdSource, options = {}) {
  const currentStep = ref('idle') // 'idle' | 'outline' | 'content' | 'complete' | 'error'
  const progress = ref(0)
  const canCancel = ref(false)
  const selectedStyle = ref('zara') // 'zara' | 'tech' | 'fun'
  const errorMessage = ref(null)
  const activityLog = ref([])
  const logPulse = ref(0)
  const isGenerating = computed(() => ['outline', 'content'].includes(currentStep.value))

  let ws = null
  let reconnectAttempts = 0
  let reconnectTimeoutId = null
  let pulseTimer = null
  let shouldReconnect = true
  const maxReconnectDelay = 30000
  let logSeq = 0
  let lastOutlineStage = ''
  let lastContentStage = ''

  const getArticleId = () => unref(articleIdSource)

  const pushLog = (text, level = 'info') => {
    if (!text) return

    const lastEntry = activityLog.value.at(-1)
    if (lastEntry && lastEntry.text === text && lastEntry.level === level) {
      return
    }

    activityLog.value = [
      ...activityLog.value,
      {
        id: `${Date.now()}-${logSeq++}`,
        text,
        level
      }
    ].slice(-8)
  }

  const resetLog = () => {
    activityLog.value = []
    logSeq = 0
  }

  const stopPulse = () => {
    if (pulseTimer) {
      clearInterval(pulseTimer)
      pulseTimer = null
    }
  }

  const startPulse = () => {
    if (pulseTimer) return

    pulseTimer = setInterval(() => {
      logPulse.value = (logPulse.value + 1) % 3
    }, 700)
  }

  const syncPulseState = (step) => {
    if (['outline', 'content'].includes(step)) {
      startPulse()
    } else {
      stopPulse()
      logPulse.value = 0
    }
  }

  const resetStageTracking = () => {
    lastOutlineStage = ''
    lastContentStage = ''
  }

  const outlineStageText = (outlineProgress) => {
    if (outlineProgress < 35) return '正在分析主题...'
    if (outlineProgress < 70) return '正在生成大纲...'
    return '正在优化结构...'
  }

  const contentStageText = (contentProgress) => {
    if (contentProgress < 20) return '正在进行结构搭建...'
    if (contentProgress < 40) return '正在进行开篇扩写...'
    if (contentProgress < 60) return '正在进行核心论证...'
    if (contentProgress < 80) return '正在进行补充示例...'
    return '正在进行收尾润色...'
  }

  const setGeneratingState = (step, nextProgress = progress.value) => {
    currentStep.value = step
    progress.value = nextProgress
    canCancel.value = ['outline', 'content'].includes(step)
    syncPulseState(step)
  }

  /**
   * Start auto-generation workflow
   * Calls /api/articles/{id}/auto-generate endpoint with selected style
   *
   * @param {string} style - Article style: 'zara', 'tech', or 'fun'
   */
  const startAutoGeneration = async (style = selectedStyle.value) => {
    const articleId = getArticleId()
    if (!articleId) {
      throw new Error('文章ID缺失，无法开始生成')
    }

    try {
      resetStageTracking()
      resetLog()
      setGeneratingState('outline', 0)
      errorMessage.value = null
      selectedStyle.value = style

      pushLog(`已提交一键生成，正在整理文章骨架（${style} 风格）`, 'running')

      const response = await fetch(
        `http://127.0.0.1:8900/api/articles/${articleId}/auto-generate?style=${style}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      )

      const data = await response.json()

      if (!data.ok) {
        throw new Error(data.error || 'Failed to start auto-generation')
      }

      pushLog('后端已接收任务，开始整理文章骨架', 'running')
      return data
    } catch (error) {
      setGeneratingState('error', 0)
      errorMessage.value = error.message
      canCancel.value = false
      syncPulseState('error')
      pushLog(`启动生成失败：${error.message}`, 'error')
      throw error
    }
  }

  /**
   * Cancel ongoing generation
   * Calls /api/articles/{id}/cancel endpoint
   */
  const cancelGeneration = async () => {
    const articleId = getArticleId()
    if (!articleId) {
      throw new Error('文章ID缺失，无法取消生成')
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8900/api/articles/${articleId}/cancel`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      )

      const data = await response.json()

      if (data.ok) {
        setGeneratingState('idle', 0)
        errorMessage.value = null
        resetStageTracking()
        syncPulseState('idle')
        pushLog('已取消生成任务', 'pending')
      }

      return data
    } catch (error) {
      console.error('Failed to cancel generation:', error)
      throw error
    }
  }

  /**
   * Handle WebSocket messages for workflow progress
   */
  const handleWebSocketMessage = (event) => {
    let data

    try {
      data = JSON.parse(event.data)
    } catch (error) {
      console.warn('[WorkflowOrchestrator] Failed to parse WebSocket payload:', error)
      return
    }

    const articleId = getArticleId()
    if (!articleId || data.article_id !== articleId) return

    const payloadProgress = Number(data.data?.progress ?? 0)

    switch (data.type) {
      case 'article_outline_generating':
        resetStageTracking()
        setGeneratingState('outline', 0)
        errorMessage.value = null
        pushLog('后端开始整理文章骨架', 'running')
        break

      case 'article_outline_progress': {
        if (currentStep.value !== 'outline') break
        const stageText = outlineStageText(payloadProgress)
        progress.value = Math.min(payloadProgress, 50)
        if (stageText !== lastOutlineStage) {
          lastOutlineStage = stageText
          pushLog(stageText, 'running')
        }
        break
      }

      case 'article_outline_generated':
        setGeneratingState('content', 50)
        pushLog('文章骨架已完成，开始扩写正文', 'done')
        break

      case 'article_content_generating':
        setGeneratingState('content', 50)
        lastContentStage = ''
        pushLog('后端开始扩写正文', 'running')
        break

      case 'article_content_progress': {
        if (currentStep.value !== 'content') break
        const stageText = contentStageText(payloadProgress)
        progress.value = 50 + Math.min(payloadProgress, 100) * 0.5
        if (stageText !== lastContentStage) {
          lastContentStage = stageText
          pushLog(stageText, 'running')
        }
        break
      }

      case 'article_content_generated':
        setGeneratingState('complete', 100)
        canCancel.value = false
        pushLog('正文已生成并同步回编辑器', 'done')
        break

      case 'article_error':
        setGeneratingState('error', 0)
        errorMessage.value = data.data?.error || 'Unknown error occurred'
        canCancel.value = false
        syncPulseState('error')
        pushLog(`生成失败：${errorMessage.value}`, 'error')
        break
    }

    if (typeof options.onArticleEvent === 'function') {
      options.onArticleEvent(data)
    }
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  const connectWebSocket = () => {
    try {
      shouldReconnect = true

      if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.close()
      }

      ws = new WebSocket('ws://127.0.0.1:8900/ws/articles')

      ws.onopen = () => {
        console.log('[WorkflowOrchestrator] WebSocket connected')
        reconnectAttempts = 0
      }

      ws.onmessage = handleWebSocketMessage

      ws.onerror = (error) => {
        console.error('[WorkflowOrchestrator] WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('[WorkflowOrchestrator] WebSocket disconnected')
        if (shouldReconnect) {
          reconnectWithBackoff()
        }
      }
    } catch (error) {
      console.error('[WorkflowOrchestrator] Failed to connect WebSocket:', error)
    }
  }

  /**
   * Reconnect WebSocket with exponential backoff
   * Implements NFR-3: WebSocket reconnection reliability
   */
  const reconnectWithBackoff = () => {
    if (!shouldReconnect) return

    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), maxReconnectDelay)
    reconnectAttempts++

    console.log(`[WorkflowOrchestrator] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)

    if (reconnectTimeoutId) {
      clearTimeout(reconnectTimeoutId)
    }

    reconnectTimeoutId = setTimeout(() => {
      reconnectTimeoutId = null
      if (shouldReconnect && (!ws || ws.readyState === WebSocket.CLOSED)) {
        connectWebSocket()
      }
    }, delay)
  }

  /**
   * Disconnect WebSocket
   */
  const disconnectWebSocket = () => {
    shouldReconnect = false

    if (reconnectTimeoutId) {
      clearTimeout(reconnectTimeoutId)
      reconnectTimeoutId = null
    }

    stopPulse()

    if (ws) {
      ws.close()
      ws = null
    }
  }

  /**
   * Reset workflow state
   */
  const reset = () => {
    setGeneratingState('idle', 0)
    resetStageTracking()
    resetLog()
    errorMessage.value = null
    syncPulseState('idle')
  }

  watch(
    () => getArticleId(),
    () => {
      reset()
    }
  )

  // Initialize WebSocket connection
  connectWebSocket()

  // Cleanup on unmount
  onUnmounted(() => {
    disconnectWebSocket()
  })

  return {
    // State
    currentStep,
    progress,
    canCancel,
    selectedStyle,
    errorMessage,
    isGenerating,
    activityLog,
    logPulse,

    // Methods
    startAutoGeneration,
    cancelGeneration,
    reset,

    // WebSocket management
    connectWebSocket,
    disconnectWebSocket
  }
}
