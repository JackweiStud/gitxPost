import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const currentTask = ref(null)
  const notifications = ref([])
  
  // 批量回复队列
  const replyQueue = ref([])  // [{url, title, author}, ...]
  const replyQueueIndex = ref(0)  // 当前处理的索引
  
  const currentQueueItem = computed(() => replyQueue.value[replyQueueIndex.value] || null)
  const queueTotal = computed(() => replyQueue.value.length)
  const queueProgress = computed(() => replyQueueIndex.value + 1)
  const hasMoreInQueue = computed(() => replyQueueIndex.value < replyQueue.value.length - 1)
  
  function setReplyQueue(items) {
    replyQueue.value = items
    replyQueueIndex.value = 0
  }
  
  function nextInQueue() {
    if (hasMoreInQueue.value) {
      replyQueueIndex.value++
      return currentQueueItem.value
    }
    return null
  }
  
  function clearReplyQueue() {
    replyQueue.value = []
    replyQueueIndex.value = 0
  }
  
  // 深色模式：默认跟随系统，或从 localStorage 读取
  const savedDarkMode = localStorage.getItem('darkMode')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const darkMode = ref(savedDarkMode !== null ? savedDarkMode === 'true' : prefersDark)
  
  // 初始化时应用主题
  function applyTheme(isDark) {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem('darkMode', isDark)
  }
  applyTheme(darkMode.value)
  
  // 监听变化自动应用
  watch(darkMode, (isDark) => applyTheme(isDark))

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleDarkMode() {
    darkMode.value = !darkMode.value
  }

  function notify(message, type = 'info', duration = 4000) {
    // 去重：如果已存在相同消息，不重复添加
    const exists = notifications.value.some(n => n.message === message && n.type === type)
    if (exists) return

    const id = Date.now()
    notifications.value.push({ id, message, type })
    
    // 限制最多显示 3 条，超出移除最旧的
    if (notifications.value.length > 3) {
      notifications.value.shift()
    }

    if (duration > 0) {
      setTimeout(() => {
        notifications.value = notifications.value.filter((n) => n.id !== id)
      }, duration)
    }
  }

  function dismissNotification(id) {
    notifications.value = notifications.value.filter((n) => n.id !== id)
  }

  function setTask(task) {
    currentTask.value = task
  }

  function clearTask() {
    currentTask.value = null
  }

  return { 
    sidebarCollapsed, currentTask, notifications, darkMode, 
    replyQueue, replyQueueIndex, currentQueueItem, queueTotal, queueProgress, hasMoreInQueue,
    toggleSidebar, toggleDarkMode, notify, dismissNotification, setTask, clearTask,
    setReplyQueue, nextInQueue, clearReplyQueue
  }
})
