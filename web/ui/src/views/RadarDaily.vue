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
              <span class="entry-date">
                {{ formatDate(r.date) }}
                <span v-if="isToday(r.date)" class="today-badge">今日</span>
              </span>
              <span class="entry-size">{{ (r.size / 1024).toFixed(1) }}K</span>
            </button>
          </div>
          <div class="empty-sidebar" v-if="!reports.length">
            <svg class="empty-icon-sm" width="40" height="40" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3" opacity="0.2"/>
              <path d="M30 40h20M40 30v20" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/>
            </svg>
            <p style="margin: 8px 0 0 0; font-size: 12px;">暂无日报</p>
          </div>
        </div>
      </aside>

      <!-- Right: Report content -->
      <div class="report-main">
        <div v-if="loading" class="skeleton-state">
          <!-- Skeleton for section header -->
          <div class="skeleton-section">
            <div class="skeleton-bar">
              <div class="skeleton-title"></div>
              <div class="skeleton-button"></div>
            </div>
            <!-- Skeleton tweet cards -->
            <div class="skeleton-grid">
              <div v-for="i in 4" :key="i" class="skeleton-card">
                <div class="skeleton-header">
                  <div class="skeleton-avatar"></div>
                  <div class="skeleton-handle"></div>
                </div>
                <div class="skeleton-line skeleton-line-lg"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line skeleton-line-sm"></div>
              </div>
            </div>
          </div>
          <!-- Skeleton for markdown content -->
          <div class="skeleton-section">
            <div class="skeleton-bar">
              <div class="skeleton-title"></div>
            </div>
            <div class="skeleton-markdown">
              <div class="skeleton-line skeleton-line-lg"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line skeleton-line-sm"></div>
            </div>
          </div>
        </div>

        <div v-else-if="!reportData" class="empty-main">
          <svg class="empty-icon" width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="20" y="15" width="40" height="50" rx="4" stroke="currentColor" stroke-width="2" opacity="0.3"/>
            <line x1="28" y1="25" x2="52" y2="25" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
            <line x1="28" y1="33" x2="48" y2="33" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
            <line x1="28" y1="41" x2="52" y2="41" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
            <line x1="28" y1="49" x2="44" y2="49" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
          </svg>
          <p class="empty-title">选择一份日报查看</p>
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
                    <div class="author-avatar" :style="{ background: getAvatarColor(tweet.author) }">{{ tweet.author[0]?.toUpperCase() }}</div>
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
            <div class="report-prose">
              <div class="markdown-body" v-html="renderedMarkdown"></div>
            </div>
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

marked.use({ gfm: true, breaks: true })
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

/**
 * 日报 Markdown 预处理：
 *  1. 把「• / ·」开头的行转为「- 」列表项 → marked 生成 <li>，获得悬挂缩进
 *  2. 把 emoji 开头（非 bullet）的分区标题行转为「## 」二级标题
 *  3. 把紧跟在列表项后的「续行」（如独占一行的 [原文↗](url)）
 *     直接拼接到上一条列表项末尾，避免 breaks:true 产生 <br> 断行
 */
function preprocessMarkdown(raw) {
  if (!raw) return ''
  const EMOJI_TITLE_RE = /^(\p{Emoji_Presentation}|\p{Extended_Pictographic})\s+\S/u
  const BULLET_RE = /^[•·]\s*/
  // 判断某行是否是"列表项的续行"：非空、非 bullet、非 emoji 标题、非空行
  const isContinuation = (t) =>
    t !== '' && !BULLET_RE.test(t) && !EMOJI_TITLE_RE.test(t) && !t.startsWith('#')

  const lines = raw.split('\n')
  const out = []
  let prevWasBullet = false

  for (const line of lines) {
    const trimmed = line.trim()

    if (BULLET_RE.test(trimmed)) {
      if (!prevWasBullet && out.length && out[out.length - 1].trim() !== '') out.push('')
      out.push('- ' + trimmed.replace(BULLET_RE, ''))
      prevWasBullet = true
    } else if (EMOJI_TITLE_RE.test(trimmed)) {
      if (prevWasBullet) out.push('')
      if (out.length && out[out.length - 1].trim() !== '') out.push('')
      out.push('## ' + trimmed)
      out.push('')
      prevWasBullet = false
    } else if (prevWasBullet && isContinuation(trimmed)) {
      // 续行：追加到上一条 list item 末尾（保持在同一行内），不换行
      const last = out[out.length - 1]
      out[out.length - 1] = last + ' ' + trimmed
      // prevWasBullet 保持 true，下一续行继续合并
    } else {
      if (prevWasBullet && trimmed !== '') out.push('')
      out.push(line)
      prevWasBullet = false
    }
  }
  return out.join('\n')
}

const renderedMarkdown = computed(() => {
  if (!reportData.value?.markdown) return ''
  return marked.parse(preprocessMarkdown(reportData.value.markdown))
})

function formatDate(dateStr) {
  const parts = dateStr.split('-')
  if (parts.length === 3) return `${parts[1]}/${parts[2]}`
  return dateStr
}

function isToday(dateStr) {
  const today = new Date()
  const yyyy = today.getFullYear()
  const mm = String(today.getMonth() + 1).padStart(2, '0')
  const dd = String(today.getDate()).padStart(2, '0')
  return dateStr === `${yyyy}-${mm}-${dd}`
}

// 根据作者名生成头像颜色（6 种预设颜色）
function getAvatarColor(author) {
  const colors = [
    'linear-gradient(135deg, #3B82F6, #2563EB)', // 蓝
    'linear-gradient(135deg, #10B981, #059669)', // 绿
    'linear-gradient(135deg, #F59E0B, #D97706)', // 琥珀
    'linear-gradient(135deg, #8B5CF6, #7C3AED)', // 紫
    'linear-gradient(135deg, #FF6B4A, #EF4444)', // 珊瑚
    'linear-gradient(135deg, #00C9A7, #14B8A6)', // 薄荷
  ]
  // 简单哈希：字符码求和
  let hash = 0
  for (let i = 0; i < author.length; i++) {
    hash += author.charCodeAt(i)
  }
  return colors[hash % colors.length]
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
  padding: 8px 10px 8px 14px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  width: 100%;
  text-align: left;
  transition: all var(--transition-fast);
  position: relative;
}
.report-entry::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: var(--accent-blue);
  border-radius: 0 2px 2px 0;
  transition: height var(--transition-fast);
}
.report-entry:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.report-entry.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.report-entry.active::before {
  height: 20px;
}
.entry-date {
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  display: flex;
  align-items: center;
  gap: 6px;
}
.today-badge {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.1);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}
.entry-size {
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.empty-sidebar {
  padding: 32px 16px;
  text-align: center;
  color: var(--text-tertiary);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.empty-icon-sm {
  color: var(--text-tertiary);
}

.report-main {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.skeleton-state {
  padding: 20px;
}
.skeleton-section {
  margin-bottom: 32px;
}
.skeleton-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.skeleton-title {
  width: 120px;
  height: 20px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}
.skeleton-button {
  width: 100px;
  height: 32px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.skeleton-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 14px;
}
.skeleton-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.skeleton-avatar {
  width: 32px;
  height: 32px;
  background: var(--bg-tertiary);
  border-radius: 50%;
}
.skeleton-handle {
  width: 80px;
  height: 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}
.skeleton-line {
  height: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
}
.skeleton-line-lg {
  height: 16px;
  width: 90%;
}
.skeleton-line-sm {
  width: 60%;
}
.skeleton-markdown {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
}

/* Shimmer animation */
.skeleton-title,
.skeleton-button,
.skeleton-avatar,
.skeleton-handle,
.skeleton-line {
  position: relative;
  overflow: hidden;
}
.skeleton-title::after,
.skeleton-button::after,
.skeleton-avatar::after,
.skeleton-handle::after,
.skeleton-line::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  to { left: 100%; }
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
  color: var(--text-tertiary);
  margin-bottom: 20px;
}
.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 4px 0;
}
.empty-hint {
  font-size: 12px;
  margin: 0;
  opacity: 0.8;
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
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
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
  padding: 24px 28px;
}
.report-prose {
  margin-top: 16px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 20px;
}

/* 报告正文容器：限制阅读宽度 + 居中 */
.report-prose .markdown-body {
  max-width: 680px;
  margin-inline: auto;
  font-size: 14.5px;
  line-height: 1.8;
  color: var(--text-primary);
}

/* ———— 正文 p（含日期 / 统计行） ———— */
.report-prose .markdown-body :deep(p) {
  margin: 0.55em 0;
  color: var(--text-secondary);
  font-size: 13.5px;
}

/* ———— 分区二级标题（## emoji 文字） ———— */
.report-prose .markdown-body :deep(h2) {
  margin-top: 2em;
  margin-bottom: 0.6em;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.015em;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent-blue);
  display: inline-block;
}
.report-prose .markdown-body :deep(h1),
.report-prose .markdown-body :deep(h3) {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 700;
  color: var(--text-primary);
}

/* ———— 列表：悬挂缩进（padding+text-indent，不用 grid，避免 <a> 被当成独立 grid item） ———— */
.report-prose .markdown-body :deep(ul) {
  list-style: none;
  padding: 0;
  margin: 0.4em 0 1.2em;
}
.report-prose .markdown-body :deep(li) {
  padding: 8px 0 8px 1.2em;
  text-indent: -1.2em;
  border-bottom: 1px dashed var(--border-subtle);
  line-height: 1.7;
  font-size: 14px;
  color: var(--text-primary);
}
.report-prose .markdown-body :deep(li:last-child) {
  border-bottom: none;
}
.report-prose .markdown-body :deep(li)::before {
  content: '·';
  color: var(--accent-blue);
  font-size: 20px;
  font-weight: 700;
  margin-right: 0.35em;
  vertical-align: middle;
}
.report-prose .markdown-body :deep(li > *) {
  text-indent: 0;
}
.report-prose .markdown-body :deep(li > p) {
  display: inline;
  margin: 0;
}

/* ———— 链接：原文↗ 内联跟随文字 ———— */
.report-prose .markdown-body :deep(a) {
  display: inline;
  color: var(--accent-blue);
  font-weight: 500;
  font-size: 0.88em;
  text-decoration: none;
  border-bottom: 1px solid rgba(26, 115, 232, 0.35);
  transition: border-color var(--transition-fast), color var(--transition-fast);
}
.report-prose .markdown-body :deep(a:hover) {
  border-bottom-color: var(--accent-blue);
  text-decoration: none;
}

/* ———— hr 分隔线 ———— */
.report-prose .markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-subtle);
  margin: 1.5em 0;
}

.report-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
