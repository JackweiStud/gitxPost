<template>
  <div class="app-layout">
    <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo" v-if="!appStore.sidebarCollapsed">
          <span class="logo-icon">g</span>
          <span class="logo-text">gitxPost</span>
        </div>
        <div class="logo-collapsed" v-else aria-hidden="true">
          <span class="logo-icon logo-icon-sm">g</span>
        </div>
        <button class="sidebar-toggle" @click="appStore.toggleSidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="appStore.sidebarCollapsed" d="M9 18l6-6-6-6" />
            <path v-else d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-label" v-if="!appStore.sidebarCollapsed">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer" v-if="!appStore.sidebarCollapsed">
        <div class="env-badge">
          <span class="env-dot"></span>
          Local
        </div>
      </div>
    </aside>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>

    <div class="toast-container">
      <transition-group name="slide">
        <div
          v-for="n in appStore.notifications"
          :key="n.id"
          class="toast"
          :class="'toast-' + n.type"
        >
          <span class="toast-message">{{ n.message }}</span>
          <button class="toast-close" @click="appStore.dismissNotification(n.id)" aria-label="关闭">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from './stores/app.js'

const appStore = useAppStore()

const navItems = [
  {
    path: '/',
    label: '概览',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  },
  {
    path: '/radar',
    label: '日报',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18"/><path d="M12 7v5l3 3"/></svg>',
  },
  {
    path: '/reply',
    label: '回帖',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  },
]
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal), min-width var(--transition-normal);
  z-index: 10;
}
.sidebar.collapsed {
  width: var(--sidebar-collapsed);
  min-width: var(--sidebar-collapsed);
}

.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px 0 16px;
  border-bottom: 1px solid var(--border-subtle);
  gap: 8px;
}
.logo-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-icon {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, var(--accent-coral) 0%, var(--accent-blue) 55%, var(--accent-mint) 100%);
  color: #fff;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 15px;
  box-shadow: var(--shadow-sm);
}
.logo-icon-sm {
  width: 28px;
  height: 28px;
  font-size: 14px;
  border-radius: 9px;
}
.logo-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.sidebar-toggle {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}
.sidebar-toggle:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.sidebar-nav {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  font-size: 13.5px;
  font-weight: 500;
}
.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  text-decoration: none;
}
.nav-item.active {
  background: linear-gradient(90deg, rgba(26, 115, 232, 0.1), rgba(0, 201, 167, 0.08));
  color: var(--text-primary);
  border: 1px solid rgba(26, 115, 232, 0.2);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-subtle);
}
.env-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 500;
}
.env-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-green);
  border-radius: 50%;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: radial-gradient(1200px 600px at 10% -10%, rgba(26, 115, 232, 0.06), transparent 55%),
    radial-gradient(900px 500px at 100% 0%, rgba(255, 107, 74, 0.05), transparent 50%),
    var(--bg-primary);
}

.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toast {
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  box-shadow: var(--shadow-md);
  max-width: 360px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.toast-message {
  flex: 1;
}
.toast-close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border-radius: var(--radius-sm);
  opacity: 0.6;
  transition: all var(--transition-fast);
  padding: 0;
  margin: 0;
}
.toast-close:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.05);
}
.toast-info {
  background: #fff;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}
.toast-success {
  background: #e6f4ea;
  color: #137333;
  border: 1px solid rgba(30, 142, 62, 0.25);
}
.toast-error {
  background: #fce8e6;
  color: #c5221f;
  border: 1px solid rgba(217, 48, 37, 0.25);
}
</style>
