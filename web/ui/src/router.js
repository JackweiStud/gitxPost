import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/radar', name: 'radar', component: () => import('./views/RadarDaily.vue') },
  { path: '/reply', name: 'reply', component: () => import('./views/ReplyWorkbench.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
