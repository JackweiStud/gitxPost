import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/radar', name: 'radar', component: () => import('./views/RadarDaily.vue') },
  { path: '/reply', name: 'reply', component: () => import('./views/ReplyWorkbench.vue') },
  { path: '/publish', name: 'publish', component: () => import('./views/PublishPage.vue') },
  { path: '/articles', name: 'articles', component: () => import('./views/ArticleListPage.vue') },
  { path: '/articles/:id', name: 'article-editor', component: () => import('./views/ArticleEditorPage.vue') },
  { path: '/accounts', name: 'accounts', component: () => import('./views/AccountsPage.vue') },
  { path: '/settings', name: 'settings', component: () => import('./views/SettingsPage.vue') },
  { path: '/followers', name: 'followers', component: () => import('./views/FollowersPage.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
