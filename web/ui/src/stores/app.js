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
    const id = Date.now()
    notifications.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => {
        notifications.value = notifications.value.filter((n) => n.id !== id)
      }, duration)
    }
  }

  function setTask(task) {
    currentTask.value = task
  }

  function clearTask() {
    currentTask.value = null
  }

  return { sidebarCollapsed, currentTask, notifications, toggleSidebar, notify, setTask, clearTask }
})
