import { ref, computed, onUnmounted } from 'vue'

/**
 * Workflow Orchestrator Composable
 * 
 * Manages the one-click auto-generation workflow for articles.
 * Handles state management, API calls, and WebSocket event listening.
 * 
 * Requirements: FR-1.1, FR-1.1.1, AC-1
 */
export function useWorkflowOrchestrator(articleId) {
  // State management
  const currentStep = ref('idle') // 'idle' | 'outline' | 'content' | 'complete' | 'error'
  const progress = ref(0) // 0-100
  const canCancel = ref(false)
  const selectedStyle = ref('zara') // 'zara' | 'tech' | 'fun'
  const errorMessage = ref(null)
  const isGenerating = computed(() => ['outline', 'content'].includes(currentStep.value))
  
  // WebSocket connection
  let ws = null
  let reconnectAttempts = 0
  const maxReconnectDelay = 30000 // 30 seconds
  
  /**
   * Start auto-generation workflow
   * Calls /api/articles/{id}/auto-generate endpoint with selected style
   * 
   * @param {string} style - Article style: 'zara', 'tech', or 'fun'
   */
  const startAutoGeneration = async (style = selectedStyle.value) => {
    try {
      currentStep.value = 'outline'
      progress.value = 0
      canCancel.value = true
      errorMessage.value = null
      selectedStyle.value = style
      
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
      
      return data
    } catch (error) {
      currentStep.value = 'error'
      errorMessage.value = error.message
      canCancel.value = false
      throw error
    }
  }
  
  /**
   * Cancel ongoing generation
   * Calls /api/articles/{id}/cancel endpoint
   */
  const cancelGeneration = async () => {
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
        currentStep.value = 'idle'
        progress.value = 0
        canCancel.value = false
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
    const data = JSON.parse(event.data)
    
    // Only process messages for this article
    if (data.article_id !== articleId) return
    
    switch (data.type) {
      case 'article_outline_generating':
        currentStep.value = 'outline'
        progress.value = 0
        canCancel.value = true
        break
        
      case 'article_outline_progress':
        if (currentStep.value === 'outline') {
          progress.value = Math.min(data.data.progress || 0, 50)
        }
        break
        
      case 'article_outline_generated':
        progress.value = 50
        // Auto-transition to content generation
        currentStep.value = 'content'
        break
        
      case 'article_content_generating':
        currentStep.value = 'content'
        progress.value = 50
        canCancel.value = true
        break
        
      case 'article_content_progress':
        if (currentStep.value === 'content') {
          // Map content progress (0-100) to overall progress (50-100)
          const contentProgress = data.data.progress || 0
          progress.value = 50 + (contentProgress * 0.5)
        }
        break
        
      case 'article_content_generated':
        currentStep.value = 'complete'
        progress.value = 100
        canCancel.value = false
        break
        
      case 'article_error':
        currentStep.value = 'error'
        errorMessage.value = data.data.error || 'Unknown error occurred'
        canCancel.value = false
        break
    }
  }
  
  /**
   * Connect to WebSocket for real-time updates
   */
  const connectWebSocket = () => {
    try {
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
        // Attempt to reconnect with exponential backoff
        reconnectWithBackoff()
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
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), maxReconnectDelay)
    reconnectAttempts++
    
    console.log(`[WorkflowOrchestrator] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)
    
    setTimeout(() => {
      if (!ws || ws.readyState === WebSocket.CLOSED) {
        connectWebSocket()
      }
    }, delay)
  }
  
  /**
   * Disconnect WebSocket
   */
  const disconnectWebSocket = () => {
    if (ws) {
      ws.close()
      ws = null
    }
  }
  
  /**
   * Reset workflow state
   */
  const reset = () => {
    currentStep.value = 'idle'
    progress.value = 0
    canCancel.value = false
    errorMessage.value = null
  }
  
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
    
    // Methods
    startAutoGeneration,
    cancelGeneration,
    reset,
    
    // WebSocket management
    connectWebSocket,
    disconnectWebSocket
  }
}
