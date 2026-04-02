<template>
  <div class="article-list-page">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">📝 文章管理</h1>
        <p class="page-subtitle">管理您的 X Article 长文内容</p>
      </div>
      <button class="btn-primary" @click="createArticle">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        新建文章
      </button>
    </div>

    <div class="articles-container" v-if="!loading">
      <div v-if="articles.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <p>还没有文章</p>
        <button class="btn-secondary" @click="createArticle">创建第一篇文章</button>
      </div>

      <div v-else class="articles-grid">
        <div
          v-for="article in articles"
          :key="article.id"
          class="article-card"
          @click="openArticle(article.id)"
        >
          <div class="card-header">
            <h3 class="article-title">{{ article.title }}</h3>
            <span class="article-status" :class="'status-' + article.status">
              {{ article.status === 'draft' ? '草稿' : '已发布' }}
            </span>
          </div>
          
          <div class="card-meta">
            <span class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              {{ formatDate(article.updated_at) }}
            </span>
            <span class="meta-item">
              步骤: {{ getStepLabel(article.step) }}
            </span>
          </div>

          <div class="card-actions" @click.stop>
            <button
              class="btn-icon"
              @click="openArticle(article.id)"
              :title="article.status === 'draft' ? '继续编辑' : '查看'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button
              class="btn-icon btn-danger"
              @click="confirmDelete(article)"
              title="删除"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="deleteDialog.show" class="dialog-overlay" @click="deleteDialog.show = false">
      <div class="dialog" @click.stop>
        <h3>确认删除</h3>
        <p>确定要删除文章「{{ deleteDialog.article?.title }}」吗？此操作无法撤销。</p>
        <div class="dialog-actions">
          <button class="btn-secondary" @click="deleteDialog.show = false">取消</button>
          <button class="btn-danger" @click="deleteArticle">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app.js'

const router = useRouter()
const appStore = useAppStore()

const loading = ref(true)
const articles = ref([])
const deleteDialog = ref({
  show: false,
  article: null
})

// 加载文章列表
const loadArticles = async () => {
  loading.value = true
  try {
    const response = await fetch('http://127.0.0.1:8900/api/articles')
    const data = await response.json()
    
    if (data.ok) {
      articles.value = data.articles
    } else {
      appStore.notify('加载文章列表失败', 'error')
    }
  } catch (error) {
    console.error('加载文章列表失败:', error)
    appStore.notify('加载文章列表失败', 'error')
  } finally {
    loading.value = false
  }
}

// 创建文章
const createArticle = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8900/api/articles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '未命名文章' })
    })
    
    const data = await response.json()
    
    if (data.ok) {
      appStore.notify('文章创建成功', 'success')
      router.push(`/articles/${data.article_id}`)
    } else {
      appStore.notify(data.error || '创建文章失败', 'error')
    }
  } catch (error) {
    console.error('创建文章失败:', error)
    appStore.notify('创建文章失败', 'error')
  }
}

// 打开文章
const openArticle = (id) => {
  router.push(`/articles/${id}`)
}

// 确认删除
const confirmDelete = (article) => {
  deleteDialog.value = {
    show: true,
    article
  }
}

// 删除文章
const deleteArticle = async () => {
  const article = deleteDialog.value.article
  if (!article) return
  
  try {
    const response = await fetch(`http://127.0.0.1:8900/api/articles/${article.id}`, {
      method: 'DELETE'
    })
    
    const data = await response.json()
    
    if (data.ok) {
      appStore.notify('文章已删除', 'success')
      articles.value = articles.value.filter(a => a.id !== article.id)
      deleteDialog.value.show = false
    } else {
      appStore.notify(data.error || '删除文章失败', 'error')
    }
  } catch (error) {
    console.error('删除文章失败:', error)
    appStore.notify('删除文章失败', 'error')
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  
  return date.toLocaleDateString('zh-CN')
}

// 获取步骤标签
const getStepLabel = (step) => {
  const labels = {
    title: '标题',
    outline: '骨架',
    content: '内容',
    preview: '预览'
  }
  return labels[step] || step
}

onMounted(() => {
  loadArticles()
})
</script>

<style scoped>
.article-list-page {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-mint));
  color: white;
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: 14px;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.articles-container {
  min-height: 400px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-tertiary);
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  margin-bottom: 20px;
}

.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.article-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.article-card:hover {
  border-color: var(--accent-blue);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.article-title {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
}

.article-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.status-draft {
  background: rgba(255, 193, 7, 0.15);
  color: #f57c00;
}

.status-published {
  background: rgba(76, 175, 80, 0.15);
  color: #2e7d32;
}

.card-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.btn-icon {
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-danger {
  color: var(--accent-coral);
}

.btn-danger:hover {
  background: rgba(255, 107, 74, 0.1);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-tertiary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.dialog h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
  color: var(--text-primary);
}

.dialog p {
  margin: 0 0 20px 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 8px 16px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border-radius: var(--radius-md);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.dialog .btn-danger {
  padding: 8px 16px;
  background: var(--accent-coral);
  color: white;
  border-radius: var(--radius-md);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.dialog .btn-danger:hover {
  background: #e64a19;
}
</style>
