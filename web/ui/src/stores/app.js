import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const currentTask = ref(null)
  const notifications = ref([])

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
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

  return { sidebarCollapsed, currentTask, notifications, toggleSidebar, notify, dismissNotification, setTask, clearTask }
})
