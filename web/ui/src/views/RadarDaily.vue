<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">日报</h1>
        <p class="page-subtitle">AI 筛选的每日推文精选</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" @click="refreshDaily" :disabled="generating">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          {{ generating ? '生成中...' : '重新生成' }}
        </button>
      </div>
    </header>

    <div class="radar-layout">
      <!-- Left: Date picker + Report list -->
      <aside class="report-sidebar">
        <div class="sidebar-section">
          <div class="section-title">历史日报</div>
          <div class="report-list">
            <button
              v-for="r in reports"
              :key="r.date"
              class="report-entry"
              :class="{ active: selectedDate === r.date }"
              @click="selectDate(r.date)"
            >
              <span class="entry-date">{{ formatDate(r.date) }}</span>
              <span class="entry-size">{{ (r.size / 1024).toFixed(1) }}K</span>
            </button>
          </div>
          <div class="empty-sidebar" v-if="!reports.length">
            暂无日报
          </div>
        </div>
      </aside>

      <!-- Right: Report content -->
      <div class="report-main">
        <div v-if="loading" class="loading-state">
          <div class="loader"></div>
          <span>加载中...</span>
        </div>

        <div v-else-if="!reportData" class="empty-main">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
          </div>
          <p>选择一份日报查看</p>
          <p class="empty-hint">或点击「重新生成」创建今日日报</p>
        </div>

        <template v-else>
          <!-- Tweet cards extracted from report -->
          <div class="tweets-section" v-if="reportData.tweets.length">
            <div class="section-bar">
              <h3>推文精选 <span class="count">{{ reportData.tweets.length }}</span></h3>
              <button
                class="btn btn-sm btn-primary"
                @click="sendSelectedToReply"
                :disabled="!selectedTweets.length"
              >
                回复选中 ({{ selectedTweets.length }})
              </button>
            </div>
            <div class="tweet-grid">
              <div
                v-for="(tweet, idx) in reportData.tweets"
                :key="idx"
                class="tweet-card"
                :class="{ selected: selectedTweets.includes(tweet.url) }"
                @click="toggleTweet(tweet.url)"
              >
                <div class="tweet-header">
                  <div class="tweet-author">
                    <div class="author-avatar">{{ tweet.author[0]?.toUpperCase() }}</div>
                    <span class="author-handle">@{{ tweet.author }}</span>
                  </div>
                  <div class="tweet-check">
                    <svg v-if="selectedTweets.includes(tweet.url)" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
                  </div>
                </div>
                <div class="tweet-title">{{ tweet.title }}</div>
                <div class="tweet-summary">{{ tweet.summary }}</div>
                <div class="tweet-footer">
                  <a :href="tweet.url" target="_blank" class="tweet-link" @click.stop>
                    原文
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                  </a>
                  <button class="tweet-reply-btn" @click.stop="goReply(tweet.url)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    回复
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Full markdown report -->
          <div class="report-content card">
            <div class="section-bar">
              <h3>完整日报</h3>
              <span class="report-meta" v-if="reportData.frontmatter">
                {{ reportData.frontmatter.llm_model || '' }} · {{ reportData.frontmatter.generated_at || '' }}
              </span>
            </div>
            <div class="markdown-body" v-html="renderedMarkdown"></div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const reports = ref([])
const selectedDate = ref(null)
const reportData = ref(null)
const loading = ref(false)
const generating = ref(false)
const selectedTweets = ref([])

const renderedMarkdown = computed(() => {
  if (!reportData.value?.markdown) return ''
  return marked.parse(reportData.value.markdown)
})

function formatDate(dateStr) {
  const parts = dateStr.split('-')
  if (parts.length === 3) return `${parts[1]}/${parts[2]}`
  return dateStr
}

function toggleTweet(url) {
  const idx = selectedTweets.value.indexOf(url)
  if (idx >= 0) selectedTweets.value.splice(idx, 1)
  else selectedTweets.value.push(url)
}

function goReply(url) {
  router.push({ path: '/reply', query: { url } })
}

function sendSelectedToReply() {
  if (!selectedTweets.value.length) return
  router.push({ path: '/reply', query: { url: selectedTweets.value[0] } })
}

async function loadReports() {
  try {
    const data = await api.getReports()
    reports.value = data.reports || []
    if (!selectedDate.value && reports.value.length) {
      const queryDate = route.query.date
      selectedDate.value = queryDate || reports.value[0].date
    }
  } catch (e) {
    appStore.notify('加载日报列表失败', 'error')
  }
}

async function loadReport(date) {
  if (!date) return
  loading.value = true
  reportData.value = null
  try {
    const data = await api.getReport(date)
    reportData.value = data
  } catch (e) {
    appStore.notify('加载日报失败: ' + e.message, 'error')
  } finally {
    loading.value = false
  }
}

function selectDate(date) {
  selectedDate.value = date
  selectedTweets.value = []
}

async function refreshDaily() {
  generating.value = true
  appStore.notify('正在生成日报，请稍候...', 'info', 15000)
  try {
    await api.runDaily()
    appStore.notify('日报生成完成', 'success')
    await loadReports()
    if (reports.value.length) {
      selectedDate.value = reports.value[0].date
    }
  } catch (e) {
    appStore.notify('日报生成失败: ' + e.message, 'error')
  } finally {
    generating.value = false
  }
}

watch(selectedDate, (d) => d && loadReport(d))

onMounted(async () => {
  await loadReports()
})
</script>

<style scoped>
.page {
  padding: 32px 40px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-shrink: 0;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
}
.page-subtitle {
  color: var(--text-tertiary);
  font-size: 13px;
  margin-top: 4px;
}

.radar-layout {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.report-sidebar {
  width: 180px;
  flex-shrink: 0;
  overflow-y: auto;
}
.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0 8px;
  margin-bottom: 8px;
}
.report-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.report-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  width: 100%;
  text-align: left;
  transition: all var(--transition-fast);
}
.report-entry:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.report-entry.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.entry-date { font-weight: 500; font-variant-numeric: tabular-nums; }
.entry-size { font-size: 10px; color: var(--text-tertiary); font-family: var(--font-mono); }

.empty-sidebar {
  padding: 16px 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.report-main {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 40px 20px;
  color: var(--text-tertiary);
  font-size: 13px;
}
.loader {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-default);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.empty-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-tertiary);
  text-align: center;
}
.empty-icon {
  margin-bottom: 16px;
  opacity: 0.3;
}
.empty-hint {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.7;
}

.tweets-section {
  margin-bottom: 24px;
}
.section-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.section-bar h3 {
  font-size: 15px;
  font-weight: 600;
}
.count {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 400;
  margin-left: 6px;
}

.tweet-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.tweet-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
}
.tweet-card:hover {
  border-color: var(--border-default);
  background: var(--bg-tertiary);
}
.tweet-card.selected {
  border-color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.04);
}

.tweet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.tweet-author {
  display: flex;
  align-items: center;
  gap: 8px;
}
.author-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
}
.author-handle {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}
.tweet-check {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
}

.tweet-title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tweet-summary {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 12px;
}

.tweet-footer {
  display: flex;
  align-items: center;
  gap: 12px;
}
.tweet-link {
  font-size: 11px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 3px;
  transition: color var(--transition-fast);
}
.tweet-link:hover {
  color: var(--accent-blue);
  text-decoration: none;
}
.tweet-reply-btn {
  font-size: 11px;
  color: var(--text-tertiary);
  background: transparent;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}
.tweet-reply-btn:hover {
  background: var(--accent-blue);
  color: #fff;
}

.report-content {
  margin-bottom: 40px;
}
.report-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}
</style>
