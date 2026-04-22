<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">雷达</h1>
        <p class="page-subtitle">AI 筛选的推文精选</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" @click="refreshReport" :disabled="generating">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          {{ generating ? '生成中...' : (activeTab === 'daily' ? '重新生成日报' : '生成周报') }}
        </button>
      </div>
    </header>

    <!-- Tab Switcher -->
    <div class="tab-switcher">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'daily' }"
        @click="switchTab('daily')"
      >
        日报
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'weekly' }"
        @click="switchTab('weekly')"
      >
        周报
      </button>
    </div>

    <div class="radar-layout">
      <!-- Daily Tab Content -->
      <template v-if="activeTab === 'daily'">
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
                <span v-if="selectedTweets.length > 1" class="batch-hint">· 将依次处理</span>
              </button>
            </div>
            <div class="tweet-grid">
              <div
                v-for="(tweet, idx) in reportData.tweets"
                :key="idx"
                class="tweet-card"
                :class="{ selected: selectedTweets.includes(idx) }"
                @click="toggleTweet(idx)"
              >
                <div class="tweet-header">
                  <div class="tweet-author">
                    <div class="author-avatar" :style="{ background: getAvatarColor(tweet.author) }">{{ tweet.author[0]?.toUpperCase() }}</div>
                    <span class="author-handle">@{{ tweet.author }}</span>
                  </div>
                  <div class="tweet-check">
                    <svg v-if="selectedTweets.includes(idx)" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
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
          <div class="report-content report-content--daily card">
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
      </template>

      <!-- Weekly Tab Content -->
      <template v-else-if="activeTab === 'weekly'">
        <!-- Left: Weekly report list -->
        <aside class="report-sidebar">
          <div class="sidebar-section">
            <div class="section-title">历史周报</div>
            <div class="report-list">
              <button
                v-for="r in weeklyReports"
                :key="r.date"
                class="report-entry"
                :class="{ active: selectedWeeklyDate === r.date }"
                @click="selectWeeklyDate(r.date)"
              >
                <span class="entry-date">
                  {{ formatDate(r.date) }}
                </span>
                <span class="entry-size">{{ (r.size / 1024).toFixed(1) }}K</span>
              </button>
            </div>
            <div class="empty-sidebar" v-if="!weeklyReports.length">
              <svg class="empty-icon-sm" width="40" height="40" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="40" cy="40" r="30" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3" opacity="0.2"/>
                <path d="M30 40h20M40 30v20" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/>
              </svg>
              <p style="margin: 8px 0 0 0; font-size: 12px;">暂无周报</p>
            </div>
          </div>
        </aside>

        <!-- Right: Weekly report content -->
        <div class="report-main">
          <!-- Weekly Pipeline Progress -->
          <div class="pipeline-progress card" v-if="weeklyGenerating">
            <div class="section-bar">
              <h3>周报生成进度</h3>
              <span class="badge badge-amber">执行中</span>
            </div>
            <div class="pipeline-steps-compact">
              <div
                v-for="(step, idx) in weeklyPipelineSteps"
                :key="step.id"
                class="pipeline-step-compact"
                :class="'step-' + step.status"
              >
                <div class="step-indicator">
                  <svg v-if="step.status === 'done'" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                  </svg>
                  <svg v-else-if="step.status === 'error'" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
                  </svg>
                  <div v-else-if="step.status === 'running'" class="spinner"></div>
                  <span v-else class="step-number">{{ idx + 1 }}</span>
                </div>
                <div class="step-info">
                  <div class="step-label">{{ step.label }}</div>
                  <div class="step-desc">{{ step.desc }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="weeklyLoading" class="skeleton-state">
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

          <div v-else-if="!weeklyReport" class="empty-main">
            <svg class="empty-icon" width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="20" y="15" width="40" height="50" rx="4" stroke="currentColor" stroke-width="2" opacity="0.3"/>
              <line x1="28" y1="25" x2="52" y2="25" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
              <line x1="28" y1="33" x2="48" y2="33" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
              <line x1="28" y1="41" x2="52" y2="41" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
              <line x1="28" y1="49" x2="44" y2="49" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
            </svg>
            <p class="empty-title">选择一份周报查看</p>
            <p class="empty-hint">或点击「生成周报」创建新周报</p>
          </div>

          <template v-else>
            <div class="report-content report-content--weekly card">
              <div class="section-bar">
                <h3>周报详情</h3>
                <span class="report-meta" v-if="weeklyReport.frontmatter">
                  {{ weeklyReport.frontmatter.llm_model || '' }} · {{ weeklyReport.frontmatter.generated_at || '' }}
                </span>
              </div>
              <div class="report-prose">
                <div class="markdown-body" v-html="renderedWeeklyMarkdown"></div>
              </div>
            </div>

            <!-- 快捷账号操作面板 -->
            <div
              class="account-actions-panel card"
              v-if="weeklyAccountActions.recommended_adds.length || weeklyAccountActions.suggested_removes.length"
            >
              <div class="section-bar">
                <h3>📡 快捷账号操作</h3>
              </div>

              <!-- 推荐关注 -->
              <div class="action-group" v-if="weeklyAccountActions.recommended_adds.length">
                <div class="action-group-title">
                  <span class="action-icon add">+</span> 推荐关注
                  <span class="count">{{ weeklyAccountActions.recommended_adds.length }}</span>
                </div>
                <div class="action-tags">
                  <div
                    v-for="item in weeklyAccountActions.recommended_adds"
                    :key="item.handle"
                    class="action-tag"
                    :class="{ done: accountActionStatus[item.handle] === 'added' }"
                  >
                    <span class="tag-handle">@{{ item.handle }}</span>
                    <span class="tag-context" v-if="item.context">{{ item.context }}</span>
                    <button
                      class="tag-btn add"
                      @click="quickAddAccount(item)"
                      :disabled="accountActionStatus[item.handle] === 'adding' || accountActionStatus[item.handle] === 'added'"
                    >
                      <template v-if="accountActionStatus[item.handle] === 'adding'">添加中...</template>
                      <template v-else-if="accountActionStatus[item.handle] === 'added'">✓ 已添加</template>
                      <template v-else>+ 添加</template>
                    </button>
                  </div>
                </div>
              </div>

              <!-- 建议移除 -->
              <div class="action-group" v-if="weeklyAccountActions.suggested_removes.length">
                <div class="action-group-title">
                  <span class="action-icon remove">×</span> 建议移除
                  <span class="count">{{ weeklyAccountActions.suggested_removes.length }}</span>
                </div>
                <div class="action-tags">
                  <div
                    v-for="item in weeklyAccountActions.suggested_removes"
                    :key="item.handle"
                    class="action-tag danger"
                    :class="{ done: accountActionStatus[item.handle] === 'removed' }"
                  >
                    <span class="tag-handle">@{{ item.handle }}</span>
                    <span class="tag-context" v-if="item.context">{{ item.context }}</span>
                    <button
                      class="tag-btn remove"
                      @click="quickRemoveAccount(item)"
                      :disabled="accountActionStatus[item.handle] === 'removing' || accountActionStatus[item.handle] === 'removed'"
                    >
                      <template v-if="accountActionStatus[item.handle] === 'removing'">移除中...</template>
                      <template v-else-if="accountActionStatus[item.handle] === 'removed'">✓ 已移除</template>
                      <template v-else>× 移除</template>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </template>
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

// Daily report state
const reports = ref([])
const selectedDate = ref(null)
const reportData = ref(null)
const loading = ref(false)
const generating = ref(false)
const selectedTweets = ref([])

// Weekly report state
const activeTab = ref('daily')
const weeklyReports = ref([])
const selectedWeeklyDate = ref(null)
const weeklyReport = ref(null)
const weeklyLoading = ref(false)
const weeklyGenerating = ref(false)

// Weekly pipeline state
const weeklyPipelineSteps = ref([
  { id: 'analyze', label: '数据分析', desc: '聚合近 7 天数据', status: 'pending' },
  { id: 'weekly', label: '生成周报', desc: 'AI 生成周报', status: 'pending' },
])

// Account actions state
const accountActionStatus = ref({})

// 从 weeklyReport 中提取账号操作数据（computed）
const weeklyAccountActions = computed(() => {
  if (!weeklyReport.value) {
    return { recommended_adds: [], suggested_removes: [] }
  }
  return {
    recommended_adds: weeklyReport.value.recommended_adds || [],
    suggested_removes: weeklyReport.value.suggested_removes || [],
  }
})

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
  let html = marked.parse(preprocessMarkdown(reportData.value.markdown))
  // 高亮 @username
  html = html.replace(/@(\w+)/g, '<span class="mention">@$1</span>')
  return html
})

const renderedWeeklyMarkdown = computed(() => {
  if (!weeklyReport.value?.markdown) return ''
  let html = marked.parse(preprocessMarkdown(weeklyReport.value.markdown))
  // 高亮 @username
  html = html.replace(/@(\w+)/g, '<span class="mention">@$1</span>')
  return html
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

function toggleTweet(tweetIdx) {
  const pos = selectedTweets.value.indexOf(tweetIdx)
  if (pos >= 0) selectedTweets.value.splice(pos, 1)
  else selectedTweets.value.push(tweetIdx)
}

function goReply(url) {
  router.push({ path: '/reply', query: { url } })
}

function sendSelectedToReply() {
  if (!selectedTweets.value.length || !reportData.value?.tweets) return
  
  // 根据索引获取所有选中推文的信息
  const queueItems = selectedTweets.value
    .map(idx => reportData.value.tweets[idx])
    .filter(Boolean)
    .map(tweet => ({
      url: tweet.url,
      title: tweet.title,
      author: tweet.author
    }))
  
  if (!queueItems.length) return
  
  // 存入批量回复队列
  appStore.setReplyQueue(queueItems)
  
  // 跳转到回帖工作台
  router.push({ path: '/reply', query: { batch: 'true' } })
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

function selectWeeklyDate(date) {
  selectedWeeklyDate.value = date
  accountActionStatus.value = {}   // 重置操作状态
}

function switchTab(tab) {
  activeTab.value = tab
  selectedTweets.value = []
  if (tab === 'weekly' && !weeklyReports.value.length) {
    loadWeeklyReports()
  }
}

async function refreshReport() {
  if (activeTab.value === 'daily') {
    await refreshDaily()
  } else {
    await refreshWeekly()
  }
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

async function refreshWeekly() {
  weeklyGenerating.value = true
  generating.value = true
  
  // 重置所有步骤状态
  weeklyPipelineSteps.value.forEach(step => step.status = 'pending')
  
  try {
    // Step 1: 分析近 7 天数据
    weeklyPipelineSteps.value[0].status = 'running'
    appStore.notify('步骤 1/2: 分析近 7 天数据...', 'info', 10000)
    const analyzeResult = await api.runAnalyze(7)
    if (!analyzeResult.ok) {
      weeklyPipelineSteps.value[0].status = 'error'
      throw new Error('分析失败: ' + (analyzeResult.error || '未知错误'))
    }
    weeklyPipelineSteps.value[0].status = 'done'
    
    // Step 2: 生成周报
    weeklyPipelineSteps.value[1].status = 'running'
    appStore.notify('步骤 2/2: AI 生成周报...', 'info', 10000)
    const result = await api.runWeekly()
    if (result.ok) {
      weeklyPipelineSteps.value[1].status = 'done'
      appStore.notify('周报生成完成！', 'success')
      await loadWeeklyReports()
      if (weeklyReports.value.length) {
        selectedWeeklyDate.value = weeklyReports.value[0].date
      }
    } else {
      weeklyPipelineSteps.value[1].status = 'error'
      const errMsg = result.error || '未知错误'
      if (errMsg.includes('API Key') || errMsg.includes('api_key')) {
        appStore.notify('LLM API Key 未配置', 'error')
      } else {
        appStore.notify('周报生成失败: ' + errMsg, 'error')
      }
    }
  } catch (e) {
    const errMsg = e.message || '未知错误'
    if (e.response?.status === 504) {
      appStore.notify('操作超时，请重试', 'error')
    } else {
      appStore.notify('周报生成失败: ' + errMsg, 'error')
    }
  } finally {
    weeklyGenerating.value = false
    generating.value = false
  }
}

async function loadWeeklyReports() {
  try {
    const data = await api.getWeeklyReports()
    weeklyReports.value = data.reports || []
    if (!selectedWeeklyDate.value && weeklyReports.value.length) {
      selectedWeeklyDate.value = weeklyReports.value[0].date
    }
  } catch (e) {
    appStore.notify('加载周报列表失败', 'error')
  }
}

async function loadWeeklyReport(date) {
  if (!date) return
  weeklyLoading.value = true
  weeklyReport.value = null
  try {
    const data = await api.getWeeklyReport(date)
    weeklyReport.value = data
    
    // 加载周报后，检查账号状态
    await syncAccountActionStatus()
  } catch (e) {
    if (e.response?.status === 404) {
      appStore.notify('该日期周报不存在', 'error')
    } else {
      appStore.notify('加载周报失败: ' + e.message, 'error')
    }
  } finally {
    weeklyLoading.value = false
  }
}

async function syncAccountActionStatus() {
  if (!weeklyReport.value) return
  
  try {
    // 获取当前监控账号列表
    const accountsData = await api.getRadarAccounts()
    const accounts = accountsData.accounts || []
    
    // 提取活跃账号和已移除账号的 handle
    const activeHandles = new Set(
      accounts.filter(a => a.status === 'active').map(a => a.handle)
    )
    const removedHandles = new Set(
      accounts.filter(a => a.status === 'removed').map(a => a.handle)
    )
    
    // 检查推荐添加的账号
    const recommendedAdds = weeklyReport.value.recommended_adds || []
    for (const item of recommendedAdds) {
      if (activeHandles.has(item.handle)) {
        accountActionStatus.value[item.handle] = 'added'
      }
    }
    
    // 检查建议移除的账号
    const suggestedRemoves = weeklyReport.value.suggested_removes || []
    for (const item of suggestedRemoves) {
      if (removedHandles.has(item.handle) || !activeHandles.has(item.handle)) {
        accountActionStatus.value[item.handle] = 'removed'
      }
    }
  } catch (e) {
    // 静默失败，不影响周报显示
    console.error('同步账号状态失败:', e)
  }
}

async function quickAddAccount(item) {
  accountActionStatus.value[item.handle] = 'adding'
  try {
    // note 使用 context 或 description，或默认 "周报推荐"
    const note = item.description || item.context || '周报推荐关注'
    await api.addRadarAccount(item.handle, note)
    accountActionStatus.value[item.handle] = 'added'
    appStore.notify(`已添加 @${item.handle}`, 'success')
  } catch (e) {
    accountActionStatus.value[item.handle] = 'error'
    // 检查是否已存在
    const msg = e.message || ''
    if (msg.includes('已在') || msg.includes('already')) {
      accountActionStatus.value[item.handle] = 'added'
      appStore.notify(`@${item.handle} 已在监控列表中`, 'info')
    } else {
      appStore.notify(`添加 @${item.handle} 失败: ${msg}`, 'error')
      // 失败时重新同步状态
      await syncAccountActionStatus()
    }
  }
}

async function quickRemoveAccount(item) {
  accountActionStatus.value[item.handle] = 'removing'
  try {
    await api.removeRadarAccount(item.handle)
    accountActionStatus.value[item.handle] = 'removed'
    appStore.notify(`已移除 @${item.handle}`, 'success')
  } catch (e) {
    accountActionStatus.value[item.handle] = 'error'
    const msg = e.message || ''
    if (msg.includes('不在') || msg.includes('not found')) {
      accountActionStatus.value[item.handle] = 'removed'
      appStore.notify(`@${item.handle} 已不在监控列表中`, 'info')
    } else {
      appStore.notify(`移除 @${item.handle} 失败: ${msg}`, 'error')
      // 失败时重新同步状态
      await syncAccountActionStatus()
    }
  }
}

watch(selectedDate, (d) => d && loadReport(d))
watch(selectedWeeklyDate, (d) => d && loadWeeklyReport(d))

onMounted(async () => {
  await loadReports()
  // Check if we should start on weekly tab
  if (route.query.tab === 'weekly') {
    activeTab.value = 'weekly'
    await loadWeeklyReports()
  }
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

.tab-switcher {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  padding: 4px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  width: fit-content;
}
.tab-btn {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}
.tab-btn:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
.tab-btn.active {
  color: var(--text-primary);
  background: var(--bg-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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
.batch-hint {
  font-size: 11px;
  opacity: 0.8;
  font-weight: 400;
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
  padding: 18px 14px 22px;
}
.report-prose {
  margin-top: 14px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 18px;
}

.report-prose .markdown-body {
  width: 100%;
  max-width: min(100%, 1024px);
  margin-inline: auto;
  padding-inline: 2px;
  font-size: 15px;
  line-height: 1.9;
  color: var(--text-primary);
  letter-spacing: 0.002em;
}

.report-content--weekly .report-prose .markdown-body {
  max-width: min(100%, 1120px);
}

/* @username 高亮 */
.report-prose .markdown-body :deep(.mention) {
  color: var(--accent-blue);
  font-weight: 500;
}

/* ———— H1 标题（周报主标题）———— */
.report-prose .markdown-body :deep(h1) {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.24;
  color: var(--text-primary);
  margin: 0 0 0.9em 0;
  padding-bottom: 14px;
  letter-spacing: -0.03em;
  border-bottom: 2px solid color-mix(in srgb, var(--accent-blue) 68%, transparent);
}

/* ———— 引用块（周报元数据）———— */
.report-prose .markdown-body :deep(blockquote) {
  margin: 1.15em 0 1.35em;
  padding: 14px 16px;
  background: color-mix(in srgb, var(--bg-tertiary) 92%, var(--accent-blue) 4%);
  border-left: 3px solid var(--accent-blue);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.75;
}
.report-prose .markdown-body :deep(blockquote p) {
  margin: 0;
}

/* ———— 正文 p（含日期 / 统计行） ———— */
.report-prose .markdown-body :deep(p) {
  margin: 0.82em 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.9;
}

/* ———— 分区二级标题（## emoji 文字） ———— */
.report-prose .markdown-body :deep(h2) {
  margin-top: 2.2em;
  margin-bottom: 0.78em;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: -0.016em;
  padding-bottom: 10px;
  border-bottom: 1px solid color-mix(in srgb, var(--accent-blue) 44%, var(--border-subtle));
  display: block;
}
.report-prose .markdown-body :deep(h3) {
  margin-top: 1.7em;
  margin-bottom: 0.55em;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.45;
  color: var(--text-primary);
}

/* ———— 表格样式 ———— */
.report-prose .markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1.3em 0;
  font-size: 13.5px;
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
}
.report-prose .markdown-body :deep(thead) {
  background: var(--bg-tertiary);
}
.report-prose .markdown-body :deep(th) {
  padding: 11px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-default);
}
.report-prose .markdown-body :deep(td) {
  padding: 11px 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  line-height: 1.65;
}
.report-prose .markdown-body :deep(tbody tr:last-child td) {
  border-bottom: none;
}
.report-prose .markdown-body :deep(tbody tr:hover) {
  background: var(--bg-hover);
}

/* ———— 列表：悬挂缩进（padding+text-indent，不用 grid，避免 <a> 被当成独立 grid item） ———— */
.report-prose .markdown-body :deep(ul) {
  list-style: none;
  padding: 0;
  margin: 0.55em 0 1.35em;
}
.report-prose .markdown-body :deep(li) {
  padding: 10px 0 10px 1.3em;
  text-indent: -1.3em;
  border-bottom: 1px dashed var(--border-subtle);
  line-height: 1.82;
  font-size: 14.5px;
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
  margin-right: 0.45em;
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
  font-weight: 600;
  font-size: 0.94em;
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

/* ———— 代码块 ———— */
.report-prose .markdown-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.88em;
  padding: 3px 7px;
  background: color-mix(in srgb, var(--bg-tertiary) 92%, var(--accent-blue) 4%);
  border-radius: var(--radius-sm);
  color: var(--accent-blue);
}
.report-prose .markdown-body :deep(pre) {
  background: color-mix(in srgb, var(--bg-tertiary) 96%, black 4%);
  padding: 14px 16px;
  border-radius: 12px;
  overflow-x: auto;
  margin: 1.15em 0;
}
.report-prose .markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text-primary);
}

/* ———— 强调文本 ———— */
.report-prose .markdown-body :deep(strong) {
  font-weight: 600;
  color: var(--text-primary);
}
.report-prose .markdown-body :deep(em) {
  font-style: italic;
  color: var(--text-secondary);
}

/* ———— 账号列表（反引号包裹的账号名）———— */
.report-prose .markdown-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.85em;
  padding: 4px 8px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-sm);
  color: var(--accent-blue);
  white-space: nowrap;
  display: inline-block;
  margin: 3px 6px 3px 0;
  line-height: 1.5;
  vertical-align: middle;
}

/* ———— 账号列表段落（包含多个账号的段落）———— */
.report-prose .markdown-body :deep(p:has(code)) {
  line-height: 2.4;
  margin: 1.05em 0;
}

/* ———— 普通段落 ———— */
.report-prose .markdown-body :deep(p:not(:has(code))) {
  line-height: 1.9;
}

/* ———— 表格中的 code 不需要特殊间距 ———— */
.report-prose .markdown-body :deep(td code) {
  margin: 0 2px;
  padding: 2px 5px;
  font-size: 0.9em;
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

/* ── 快捷账号操作面板 ───────────────────── */
.account-actions-panel {
  margin-top: 16px;
  padding: 20px;
}
.action-group {
  margin-bottom: 16px;
}
.action-group:last-child {
  margin-bottom: 0;
}
.action-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}
.action-icon.add {
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
}
.action-icon.remove {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}
.action-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.action-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  font-size: 12px;
  transition: all var(--transition-fast);
}
.action-tag:hover {
  border-color: var(--accent-blue);
}
.action-tag.danger {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.2);
}
.action-tag.danger:hover {
  border-color: #EF4444;
  background: rgba(239, 68, 68, 0.08);
}
.action-tag.done {
  opacity: 0.5;
  background: var(--bg-tertiary);
}
.tag-handle {
  font-weight: 600;
  color: var(--accent-blue);
}
.action-tag.danger .tag-handle {
  color: #DC2626;
}
.tag-context {
  color: var(--text-tertiary);
  font-size: 11px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-tag.danger .tag-context {
  color: #991B1B;
}
.tag-btn {
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  white-space: nowrap;
}
.tag-btn.add {
  color: #10B981;
  background: rgba(16, 185, 129, 0.08);
}
.tag-btn.add:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.18);
}
.tag-btn.remove {
  color: #ffffff;
  background: #EF4444;
}
.tag-btn.remove:hover:not(:disabled) {
  background: #DC2626;
}
.tag-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

/* ── 周报流水线进度 ───────────────────── */
.pipeline-progress {
  margin-bottom: 20px;
  padding: 20px;
}
.pipeline-steps-compact {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}
.pipeline-step-compact {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  transition: all var(--transition-fast);
}
.pipeline-step-compact.step-running {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
}
.pipeline-step-compact.step-done {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
}
.pipeline-step-compact.step-error {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
}
.step-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  font-weight: 600;
  font-size: 13px;
}
.step-running .step-indicator {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}
.step-done .step-indicator {
  background: rgba(16, 185, 129, 0.15);
  color: #10B981;
}
.step-error .step-indicator {
  background: rgba(239, 68, 68, 0.15);
  color: #EF4444;
}
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(59, 130, 246, 0.3);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.step-info {
  flex: 1;
}
.step-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.step-desc {
  font-size: 11px;
  color: var(--text-tertiary);
}
.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
}
.badge-amber {
  color: #F59E0B;
  background: rgba(245, 158, 11, 0.1);
}
</style>
