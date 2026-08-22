<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">概览</h1>
        <p class="page-subtitle">gitxPost 工作台</p>
      </div>
      <div v-if="pipelineRunning" class="header-actions">
        <p class="pipeline-hint">
          全流程约 5–15 分钟（视网络与账号量）。重复点击不会并行执行；可随时点「停止」。
        </p>
        <button
          type="button"
          class="btn btn-danger btn-lg"
          @click="stopPipeline"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>
          停止
        </button>
      </div>
    </header>

    <!-- Stats Grid with Refresh -->
    <div class="stats-header">
      <div class="stats-meta">
        <span v-if="lastUpdateText" class="update-time">{{ lastUpdateText }}</span>
      </div>
      <button class="btn-icon" @click="manualRefresh" :disabled="isRefreshing" title="刷新数据">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: isRefreshing }">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
        </svg>
      </button>
    </div>

    <!-- Stats Grid - Group Cards -->
    <div class="stats-grid-grouped">
      <!-- 雷达状态 -->
      <div class="stat-group-card">
        <div class="group-header">
          <div class="group-icon group-icon-blue">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          </div>
          <span class="group-title">雷达状态</span>
        </div>
        <div class="group-main">
          <div class="group-value">{{ status?.scan?.last_scan_time || '--' }}</div>
          <div class="group-label">最近扫描</div>
        </div>
        <div class="group-stats">
          <div class="group-stat">
            <span class="stat-num">{{ status?.scan?.total_accounts || 0 }}</span>
            <span class="stat-text">监控</span>
          </div>
          <div class="group-stat-divider"></div>
          <div class="group-stat">
            <span class="stat-num">{{ status?.scan?.new_tweets || 0 }}</span>
            <span class="stat-text">新推</span>
          </div>
        </div>
      </div>

      <!-- 粉丝增长 -->
      <div class="stat-group-card stat-group-card-horizontal clickable" @click="$router.push('/followers')">
        <div class="group-left">
          <div class="group-header">
            <div class="group-icon group-icon-red">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            <span class="group-title">粉丝增长</span>
            <span v-if="followersData.changeText" class="group-badge" :class="{
              'badge-positive': followersData.change > 0,
              'badge-negative': followersData.change < 0,
              'badge-neutral': followersData.change === 0
            }">
              {{ followersData.changeText }}
            </span>
          </div>
          <div class="group-main">
            <div class="group-value large">{{ followersData.count }}</div>
            <div class="group-label">当前粉丝</div>
          </div>
          <div class="group-hint">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
            点击查看详情
          </div>
        </div>
        <div v-if="followersSparkline.path" class="group-trend group-trend-right">
          <div class="group-trend-meta">
            <span class="group-trend-label">趋势</span>
            <span class="group-trend-range">共 {{ followersSparkline.days }} 天</span>
          </div>
          <svg :viewBox="`0 0 ${sparklineWidth} ${sparklineHeight}`" class="group-trend-chart" aria-hidden="true">
            <defs>
              <linearGradient id="gradient-followers" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:var(--accent-blue);stop-opacity:0.2" />
                <stop offset="100%" style="stop-color:var(--accent-blue);stop-opacity:0" />
              </linearGradient>
            </defs>
            <line
              x1="0"
              :y1="sparklineHeight - 3"
              :x2="sparklineWidth"
              :y2="sparklineHeight - 3"
              class="group-trend-baseline"
            />
            <path v-if="followersSparkline.fillPath" :d="followersSparkline.fillPath" fill="url(#gradient-followers)" />
            <path :d="followersSparkline.path" class="group-trend-line group-trend-line-followers" />
            <circle
              v-if="followersSparkline.lastPoint"
              :cx="followersSparkline.lastPoint.x"
              :cy="followersSparkline.lastPoint.y"
              r="2.5"
              class="group-trend-dot group-trend-dot-followers"
            />
          </svg>
        </div>
      </div>

      <!-- 内容生产 -->
      <div class="stat-group-card stat-group-card-horizontal clickable" @click="$router.push('/followers')">
        <div class="group-left">
          <div class="group-header">
            <div class="group-icon group-icon-orange">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <span class="group-title">内容生产</span>
          </div>
          <div class="group-main">
            <div class="group-value large">{{ followersData.activity }}</div>
            <div class="group-label">24h 活动</div>
          </div>
          <div class="group-hint">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
            点击查看详情
          </div>
        </div>
        <div v-if="activitySparkline.path" class="group-trend group-trend-right">
          <div class="group-trend-meta">
            <span class="group-trend-label">趋势</span>
            <span class="group-trend-range">共 {{ activitySparkline.days }} 天</span>
          </div>
          <svg :viewBox="`0 0 ${sparklineWidth} ${sparklineHeight}`" class="group-trend-chart" aria-hidden="true">
            <defs>
              <linearGradient id="gradient-activity" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#f97316;stop-opacity:0.2" />
                <stop offset="100%" style="stop-color:#f97316;stop-opacity:0" />
              </linearGradient>
            </defs>
            <line
              x1="0"
              :y1="sparklineHeight - 3"
              :x2="sparklineWidth"
              :y2="sparklineHeight - 3"
              class="group-trend-baseline"
            />
            <path v-if="activitySparkline.fillPath" :d="activitySparkline.fillPath" fill="url(#gradient-activity)" />
            <path :d="activitySparkline.path" class="group-trend-line group-trend-line-activity" />
            <circle
              v-if="activitySparkline.lastPoint"
              :cx="activitySparkline.lastPoint.x"
              :cy="activitySparkline.lastPoint.y"
              r="2.5"
              class="group-trend-dot group-trend-dot-activity"
            />
          </svg>
        </div>
      </div>

      <!-- 最佳发帖时间 -->
      <div class="stat-group-card best-time-card">
        <div class="group-header">
          <div class="group-icon group-icon-cyan">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <span class="group-title">推荐发帖时间</span>
        </div>
        <div class="group-main">
          <div class="group-value best-time-value">{{ bestTimeTopWindow?.time || '--' }}</div>
          <div class="group-label">{{ bestTimeRunning ? '正在估算' : '每日推荐窗口' }}</div>
          <div v-if="bestTimeReasonLines.length" class="best-time-reason">
            <div v-for="line in bestTimeReasonLines" :key="line">{{ line }}</div>
          </div>
        </div>
        <div class="best-time-meta">
          <span>{{ bestTimeMetaText }}</span>
        </div>
      </div>
    </div>

    <div class="focus-grid">
      <div class="card activity-card">
        <div class="card-header activity-card-header">
          <div>
            <p class="card-eyebrow">最近动作</p>
            <h3>把扫描、日报、调度串起来看</h3>
          </div>
          <span v-if="lastUpdateText" class="activity-refresh">最近刷新 {{ lastUpdateText }}</span>
        </div>
        <div class="timeline-list">
          <div
            v-for="item in activityTimeline"
            :key="item.id"
            class="timeline-item"
          >
            <div class="timeline-rail">
              <div class="timeline-marker" :class="'timeline-marker-' + item.tone">
                <span></span>
              </div>
              <div class="timeline-line"></div>
            </div>
            <div class="timeline-body">
              <div class="timeline-meta">
                <span class="timeline-kicker">{{ item.kicker }}</span>
                <span class="timeline-time">{{ item.time }}</span>
              </div>
              <div class="timeline-main">
                <div class="timeline-copy">
                  <div class="timeline-title">{{ item.title }}</div>
                  <div class="timeline-detail">{{ item.detail }}</div>
                </div>
                <button
                  type="button"
                  class="timeline-action"
                  @click="handleTimelineAction(item.action)"
                >
                  {{ item.cta }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card focus-actions-card">
        <div class="card-header">
          <div>
            <p class="card-eyebrow">下一步建议</p>
            <h3>现在可以这样继续</h3>
          </div>
        </div>
        <div class="focus-actions">
          <button
            v-for="action in focusActions"
            :key="action.id"
            type="button"
            class="focus-action"
            :disabled="action.disabled"
            @click="handleFocusAction(action.id)"
          >
            <div class="focus-action-body">
              <span class="focus-action-title">{{ action.title }}</span>
              <span class="focus-action-desc">{{ action.desc }}</span>
            </div>
            <span class="focus-action-cta">{{ action.cta }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Pipeline Progress -->
    <div class="card pipeline-card" v-if="pipelineRunning || pipelineResult">
      <div class="card-header">
        <h3>流水线执行</h3>
        <span
          class="badge"
          :class="
            pipelineRunning
              ? userStoppedPipeline
                ? 'badge-purple'
                : 'badge-amber'
              : pipelineResult?.cancelled
                ? 'badge-purple'
                : pipelineResult?.ok
                  ? 'badge-green'
                  : 'badge-red'
          "
        >
          {{
            pipelineRunning
              ? userStoppedPipeline
                ? '正在停止'
                : '执行中'
              : pipelineResult?.cancelled
                ? '已停止'
                : pipelineResult?.ok
                  ? '完成'
                  : '失败'
          }}
        </span>
      </div>
      <div class="pipeline-steps">
        <div
          v-for="(step, idx) in pipelineSteps"
          :key="step.id"
          class="pipeline-step"
          :class="'step-' + step.status"
        >
          <div class="step-indicator">
            <div class="step-dot">
              <svg v-if="step.status === 'done'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <svg v-else-if="step.status === 'error'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              <div v-else-if="step.status === 'running'" class="step-spinner"></div>
              <span v-else class="step-number">{{ idx + 1 }}</span>
            </div>
            <div class="step-line" v-if="idx < pipelineSteps.length - 1"></div>
          </div>
          <div class="step-content">
            <div class="step-name">
              {{ step.label }}
              <span v-if="step.status === 'running' && step.startTime" class="step-time">
                · 已用 {{ getElapsedTime(step.startTime) }}
              </span>
              <span v-else-if="step.status === 'done' && step.duration" class="step-time">
                · 用时 {{ step.duration }}
              </span>
            </div>
            <div class="step-desc">{{ step.desc }} <span class="step-estimate">· 预计 {{ step.estimate }}</span></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Scheduler: Compact status bar when installed, full card when not -->
    <div v-if="schedulerStatus?.installed" class="scheduler-bar">
      <div class="scheduler-bar-info">
        <span class="scheduler-status-dot"></span>
        <span class="scheduler-bar-text">
          定时任务运行中 · 每天 {{ schedulerStatus.scheduled_time || '—' }}
          <span v-if="schedulerStatus.last_run" class="scheduler-last-run"> · 上次 {{ formatLastRun(schedulerStatus.last_run) }}</span>
        </span>
      </div>
      <div class="scheduler-bar-actions">
        <button class="btn-link primary" type="button" @click="runSchedulerNow" :disabled="schedulerRunning">
          {{ schedulerRunning ? '执行中…' : '立即执行' }}
        </button>
        <button class="btn-link" @click="toggleLogs">{{ showLogs ? '隐藏日志' : '查看日志' }}</button>
        <button class="btn-link" @click="showInstallModal = true">修改时间</button>
        <button class="btn-link danger" @click="uninstallScheduler">卸载</button>
      </div>
    </div>

    <!-- Full scheduler card when not installed -->
    <div class="card scheduler-card" v-else>
      <div class="card-header">
        <h3>定时任务</h3>
        <span class="badge badge-gray">🔴 未安装</span>
      </div>
      <div class="scheduler-empty">
        <p>定时任务未安装，安装后将每天自动执行扫描、日报和粉丝统计。</p>
      </div>
      <div class="scheduler-actions">
        <button class="btn btn-primary" @click="showInstallModal = true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          安装调度器
        </button>
      </div>
    </div>

    <!-- Scheduler logs (shown below bar when expanded) -->
    <div v-if="schedulerStatus?.installed && showLogs && schedulerLogs" class="scheduler-logs-standalone">
      <div class="logs-header">
        <span class="logs-title">最近日志 ({{ schedulerLogs.log_file }})</span>
        <button class="btn-icon" @click="loadSchedulerLogs">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
        </button>
      </div>
      <pre class="logs-content">{{ schedulerLogs.logs.join('\n') }}</pre>
    </div>

    <!-- Install Scheduler Modal -->
    <div v-if="showInstallModal" class="modal-overlay" @click.self="showInstallModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ schedulerStatus?.installed ? '修改执行时间' : '安装定时任务' }}</h3>
          <button class="btn-icon" @click="showInstallModal = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <label class="form-label">执行时间</label>
          <input
            type="time"
            v-model="installTime"
            class="form-input"
          />
          <p class="form-hint">调度器将在每天指定时间自动执行扫描、日报和粉丝统计任务</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="showInstallModal = false">取消</button>
          <button class="btn btn-primary" @click="installScheduler" :disabled="installing">
            {{ installing ? '安装中...' : (schedulerStatus?.installed ? '确认修改' : '确认安装') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const appStore = useAppStore()
const router = useRouter()
const status = ref(null)
const reports = ref([])
const followers = ref(null)
const bestTimeAnalysis = ref(null)
const bestTimeRunning = ref(false)
const pipelineRunning = ref(false)
const pipelineResult = ref(null)
const pipelineAbort = ref(null)
const userStoppedPipeline = ref(false)
const lastUpdateTime = ref(null)
const isRefreshing = ref(false)
const now = ref(Date.now())
let timer = null
const sparklineWidth = 160
const sparklineHeight = 38

// Scheduler state
const schedulerStatus = ref(null)
const showInstallModal = ref(false)
const installTime = ref('09:00')
const installing = ref(false)
const schedulerRunning = ref(false)
const showLogs = ref(false)
const schedulerLogs = ref(null)

const pipelineSteps = ref([
  { id: 'scan', label: '雷达扫描', desc: 'auto：RSS 失败则 CDP，最多 100 账号', estimate: '约 15-40 分钟', status: 'pending', startTime: null, duration: null },
  { id: 'daily', label: '生成日报', desc: 'AI 筛选并生成 Markdown 日报', estimate: '2-5 分钟', status: 'pending', startTime: null, duration: null },
])

// 计算已用时间
function getElapsedTime(startTime) {
  if (!startTime) return ''
  const seconds = Math.floor((now.value - startTime) / 1000)
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}分${secs}秒`
}

// 格式化持续时间
function formatDuration(ms) {
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}分${secs}秒`
}

function formatBestTimeAnalysisTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

// 计算上次更新时间的相对显示
const lastUpdateText = computed(() => {
  if (!lastUpdateTime.value) return ''
  const seconds = Math.floor((now.value - lastUpdateTime.value) / 1000)
  if (seconds < 10) return '刚刚更新'
  if (seconds < 60) return `${seconds} 秒前`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  return `${hours} 小时前`
})

// 计算粉丝数据
const sortedFollowerRecords = computed(() => {
  if (!followers.value?.records?.length) return []
  return [...followers.value.records].sort((a, b) => a.date.localeCompare(b.date))
})

const validFollowerTrendRecords = computed(() =>
  sortedFollowerRecords.value.filter((record) => record.followers >= 0)
)

const followersData = computed(() => {
  if (!sortedFollowerRecords.value.length) {
    return { count: '--', change: 0, changeText: '', activity: '--' }
  }
  
  const records = sortedFollowerRecords.value
  const latest = records[records.length - 1]
  const count = latest.followers || 0
  const activity = latest.activity_24h ?? '--'
  
  // 计算变化（相比前一天）
  let change = 0
  let changeText = ''
  
  if (records.length > 1) {
    const previous = records[records.length - 2]
    change = count - (previous.followers || 0)
    
    if (change > 0) {
      changeText = `+${change}`
    } else if (change < 0) {
      changeText = `${change}`
    } else {
      changeText = '持平'
    }
  }
  
  return { count, change, changeText, activity }
})

const scanData = computed(() => status.value?.scan || {})
const latestReport = computed(() => reports.value[0] || null)
const latestFollowerRecord = computed(() => {
  if (!sortedFollowerRecords.value.length) return null
  return sortedFollowerRecords.value.at(-1) || null
})
const activePipelineStep = computed(() => pipelineSteps.value.find((step) => step.status === 'running') || null)
const bestTimeTopWindow = computed(() => {
  const rec = bestTimeAnalysis.value?.daily_recommendations?.[0]
  if (!rec) return null
  return {
    time: rec.time?.replace(/\s*\(.*\)$/, '') || '暂无结果',
    score: Number.isFinite(rec.final_score) ? rec.final_score.toFixed(2) : '--',
    posts: rec.radar_posts ?? '--',
    audienceScore: Number.isFinite(rec.audience_score) ? rec.audience_score.toFixed(1) : '--',
    competitionScore: Number.isFinite(rec.competition_score) ? rec.competition_score.toFixed(1) : '--',
    overlapScore: Number.isFinite(rec.overlap_score) ? rec.overlap_score.toFixed(1) : '--',
    reason: rec.reason || '',
  }
})
const bestTimeReasonLines = computed(() => {
  if (!bestTimeTopWindow.value) return []
  return [
    `情况：欧美受众活跃: ${bestTimeTopWindow.value.audienceScore} | 避堵竞争度: ${bestTimeTopWindow.value.competitionScore} | 欧美重叠度: ${bestTimeTopWindow.value.overlapScore}`,
    `特征：硅谷${bestTimeTopWindow.value.reason}`,
  ]
})
const bestTimeMetaText = computed(() => {
  if (!bestTimeAnalysis.value) return '暂无历史结果'
  const posts = bestTimeAnalysis.value.total_posts_analyzed ?? '--'
  const updated = formatBestTimeAnalysisTime(bestTimeAnalysis.value.analysis_time)
  return `${posts} 条样本${updated ? ` · ${updated}` : ''}`
})

function buildSparklineModel(records, getValue, { minZero = false } = {}) {
  if (records.length < 2) {
    return { path: '', fillPath: '', lastPoint: null, days: records.length }
  }

  const values = records.map(getValue).filter((value) => Number.isFinite(value))
  if (values.length < 2) {
    return { path: '', fillPath: '', lastPoint: null, days: values.length }
  }

  const minVal = minZero ? 0 : Math.min(...values)
  const maxVal = minZero ? Math.max(...values, 1) : Math.max(...values)
  const range = maxVal - minVal || 1
  const yPad = range * 0.1
  const plotW = sparklineWidth - 6
  const plotH = sparklineHeight - 8

  const points = values.map((value, index) => {
    const x = 3 + (index / (values.length - 1)) * plotW
    const y = 4 + plotH - ((value - minVal + yPad) / (range + yPad * 2)) * plotH
    return {
      x: Number(x.toFixed(2)),
      y: Number(y.toFixed(2))
    }
  })

  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')

  // 创建填充路径：从第一个点开始，沿着线条，然后沿底部返回
  const baselineY = sparklineHeight - 3
  const fillPath = points.length > 0
    ? `M ${points[0].x} ${baselineY} L ${points[0].x} ${points[0].y} ` +
      points.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ') +
      ` L ${points[points.length - 1].x} ${baselineY} Z`
    : ''

  return {
    path: linePath,
    fillPath,
    lastPoint: points.at(-1) || null,
    days: values.length
  }
}

const followersSparkline = computed(() =>
  buildSparklineModel(validFollowerTrendRecords.value, (record) => record.followers)
)

const activitySparkline = computed(() =>
  buildSparklineModel(validFollowerTrendRecords.value, (record) => record.activity_24h ?? 0, { minZero: true })
)

const focusActions = computed(() => {
  const actions = []
  const latestReportDate = latestReport.value?.date

  if (pipelineRunning.value) {
    actions.push({
      id: 'stop-pipeline',
      title: '停止当前流水线',
      desc: '如果本轮执行方向不对，可以立刻终止，避免继续占用时间。',
      cta: '停止'
    })
  } else {
    actions.push({
      id: 'run-pipeline',
      title: latestReportDate ? '重新生成今日日报' : '生成今日日报',
      desc: latestReportDate
        ? '重新执行扫描和日报生成，刷新今天的话题池与精选内容。'
        : '执行扫描和日报生成，先把今天的内容池建立起来。',
      cta: latestReportDate ? '重新生成' : '开始生成'
    })
  }

  if (latestReportDate) {
    actions.push({
      id: 'open-radar',
      title: '查看今日日报',
      desc: `最新日报 ${latestReportDate} 已可查看，先快速判断今天哪些话题值得跟进。`,
      cta: '打开日报'
    })
  }

  actions.push({
    id: 'best-time',
    title: '获取最佳发帖时间估计',
    desc: bestTimeTopWindow.value
      ? `当前建议 ${bestTimeTopWindow.value.time}，综合评分 ${bestTimeTopWindow.value.score}。`
      : '基于最近 7 天雷达样本，估算欧美用户更适合的北京时间发帖窗口。',
    cta: bestTimeRunning.value ? '估算中' : '开始估算',
    disabled: bestTimeRunning.value
  })

  actions.push({
    id: 'open-reply',
    title: '进入回帖工作台',
    desc: '把感兴趣的推文带去生成回复，尽快把内容转成互动。',
    cta: '去回帖'
  })

  if (!schedulerStatus.value?.installed) {
    actions.push({
      id: 'open-scheduler',
      title: '开启自动执行',
      desc: '装上调度器后，每天会自动扫描、生成日报并更新粉丝统计。',
      cta: '安装调度器'
    })
  } else {
    actions.push({
      id: 'open-followers',
      title: '查看粉丝变化',
      desc: followersData.value.changeText
        ? `当前粉丝 ${followersData.value.count}，较上一天 ${followersData.value.changeText}。`
        : '看看粉丝增长与活跃度，判断内容产出有没有带来反馈。',
      cta: '看趋势'
    })
  }

  return actions.slice(0, 4)
})

const activityTimeline = computed(() => {
  const items = []

  if (pipelineRunning.value) {
    items.push({
      id: 'pipeline',
      kicker: '当前进行中',
      time: activePipelineStep.value?.startTime ? `已运行 ${getElapsedTime(activePipelineStep.value.startTime)}` : '正在执行',
      title: activePipelineStep.value?.label || '日报流水线',
      detail: activePipelineStep.value?.desc || '扫描与日报生成正在推进中，完成后首页会自动刷新。',
      cta: '看执行区',
      action: 'scroll-pipeline',
      tone: 'running'
    })
  }

  items.push({
    id: 'scan',
    kicker: '雷达扫描',
    time: scanData.value.last_scan_time || '暂无扫描记录',
    title: scanData.value.last_scan_time ? '最近扫描已完成' : '还没有扫描记录',
    detail: `当前监控 ${scanData.value.total_accounts || 0} 个账号，最近新发现 ${scanData.value.new_tweets || 0} 条推文。`,
    cta: pipelineRunning.value ? '执行中' : '重跑扫描',
    action: pipelineRunning.value ? 'noop' : 'scan',
    tone: scanData.value.last_scan_time ? ((scanData.value.new_tweets || 0) > 0 ? 'attention' : 'done') : 'pending'
  })

  items.push({
    id: 'daily',
    kicker: '日报生成',
    time: latestReport.value?.date || '暂无日报',
    title: latestReport.value ? `最新日报 ${latestReport.value.date}` : '今天还没有日报',
    detail: latestReport.value
      ? `最近一份日报大小 ${(latestReport.value.size / 1024).toFixed(1)}KB，可以直接进入日报页查看精选内容。`
      : '建议先跑一次完整流水线，把今天的话题池和精选内容先生成出来。',
    cta: latestReport.value ? '查看日报' : '生成日报',
    action: latestReport.value ? 'open-radar' : 'run-pipeline',
    tone: latestReport.value ? 'done' : 'pending'
  })

  items.push({
    id: 'scheduler',
    kicker: '自动调度',
    time: schedulerStatus.value?.installed
      ? (schedulerStatus.value.last_run ? formatLastRun(schedulerStatus.value.last_run) : `每天 ${schedulerStatus.value.scheduled_time || '—'}`)
      : '未安装',
    title: schedulerStatus.value?.installed ? '调度器已启用' : '还没有自动调度',
    detail: schedulerStatus.value?.installed
      ? `当前设定为每天 ${schedulerStatus.value.scheduled_time || '—'} 自动执行${schedulerStatus.value.last_run ? '，最近一次已执行完成。' : '，等待首次执行。'}`
      : '安装后可以把扫描、日报和粉丝统计变成自动流程，不需要每天手动点一次。',
    cta: schedulerStatus.value?.installed ? '查看日志' : '安装',
    action: schedulerStatus.value?.installed ? 'toggle-logs' : 'open-scheduler',
    tone: schedulerStatus.value?.installed ? 'done' : 'pending'
  })

  items.push({
    id: 'followers',
    kicker: '粉丝快照',
    time: latestFollowerRecord.value?.date || '暂无记录',
    title: latestFollowerRecord.value ? '粉丝趋势已更新' : '还没有粉丝快照',
    detail: latestFollowerRecord.value
      ? `当前粉丝 ${followersData.value.count}，24h 活动 ${followersData.value.activity ?? '--'}${followersData.value.changeText ? `，较上一天 ${followersData.value.changeText}。` : '。'}`
      : '建议打开粉丝页采集一次，首页就能更完整地反映增长和活跃变化。',
    cta: '看趋势',
    action: 'open-followers',
    tone: followersData.value.change > 0 ? 'positive' : (latestFollowerRecord.value ? 'done' : 'pending')
  })

  return items
})

function handleFocusAction(actionId) {
  switch (actionId) {
    case 'run-pipeline':
      runFullPipeline()
      break
    case 'stop-pipeline':
      stopPipeline()
      break
    case 'open-radar':
      router.push('/radar')
      break
    case 'best-time':
      runBestTimeAnalysis()
      break
    case 'open-reply':
      router.push('/reply')
      break
    case 'open-followers':
      router.push('/followers')
      break
    case 'open-scheduler':
      showInstallModal.value = true
      break
  }
}

async function handleTimelineAction(actionId) {
  switch (actionId) {
    case 'scan':
      await runScanOnly()
      break
    case 'run-pipeline':
      await runFullPipeline()
      break
    case 'open-radar':
      router.push('/radar')
      break
    case 'open-followers':
      router.push('/followers')
      break
    case 'open-scheduler':
      showInstallModal.value = true
      break
    case 'toggle-logs':
      if (!showLogs.value) {
        showLogs.value = true
        if (!schedulerLogs.value) {
          await loadSchedulerLogs()
        }
      } else {
        showLogs.value = false
      }
      break
    case 'scroll-pipeline':
      document.querySelector('.pipeline-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      break
    case 'noop':
      break
  }
}

async function loadData() {
  if (isRefreshing.value) return
  isRefreshing.value = true
  try {
    const [s, r, f, sched, bestTime] = await Promise.all([
      api.getStatus(), 
      api.getReports(),
      api.getFollowers(),
      api.getSchedulerStatus(),
      api.getBestTimeAnalysis()
    ])
    status.value = s
    reports.value = r.reports || []
    followers.value = f
    schedulerStatus.value = sched
    bestTimeAnalysis.value = bestTime.analysis || null
    lastUpdateTime.value = Date.now()
  } catch (e) {
    appStore.notify('加载数据失败: ' + e.message, 'error')
  } finally {
    isRefreshing.value = false
  }
}

async function manualRefresh() {
  appStore.notify('正在刷新数据...', 'info', 2000)
  await loadData()
}

function isAbortError(e) {
  const c = e?.code
  const n = e?.name
  const m = (e?.message || '').toLowerCase()
  return c === 'ERR_CANCELED' || n === 'CanceledError' || m.includes('canceled') || m.includes('cancelled')
}

async function stopPipeline() {
  userStoppedPipeline.value = true
  try {
    await api.cancelRadar()
  } catch (e) {
    appStore.notify('停止接口调用失败: ' + e.message, 'error')
  }
  pipelineAbort.value?.abort()
  appStore.notify('已请求终止后台任务（子进程被杀死后当前步骤会结束）', 'info', 6000)
}

async function runFullPipeline() {
  if (pipelineRunning.value) return
  userStoppedPipeline.value = false
  pipelineRunning.value = true
  pipelineResult.value = null
  pipelineAbort.value = new AbortController()
  const sig = { signal: pipelineAbort.value.signal }
  pipelineSteps.value.forEach((s) => {
    s.status = 'pending'
    s.startTime = null
    s.duration = null
  })

  const stepFns = [() => api.runScan(sig), () => api.runDaily(sig)]

  try {
    for (let i = 0; i < stepFns.length; i++) {
      if (userStoppedPipeline.value) {
        pipelineSteps.value[i].status = 'pending'
        break
      }
      pipelineSteps.value[i].status = 'running'
      pipelineSteps.value[i].startTime = Date.now()
      try {
        const result = await stepFns[i]()
        const elapsed = Date.now() - pipelineSteps.value[i].startTime
        pipelineSteps.value[i].duration = formatDuration(elapsed)
        if (userStoppedPipeline.value) {
          pipelineSteps.value[i].status = 'error'
          pipelineResult.value = { ok: false, cancelled: true }
          appStore.notify('流水线已中止', 'info')
          break
        }
        pipelineSteps.value[i].status = result.ok !== false ? 'done' : 'error'
        if (result.ok === false) {
          pipelineResult.value = { ok: false }
          appStore.notify(`步骤「${pipelineSteps.value[i].label}」失败`, 'error')
          break
        }
      } catch (e) {
        if (isAbortError(e) || userStoppedPipeline.value) {
          pipelineSteps.value[i].status = 'error'
          pipelineResult.value = { ok: false, cancelled: true }
          appStore.notify('流水线已中止', 'info')
          break
        }
        pipelineSteps.value[i].status = 'error'
        pipelineResult.value = { ok: false }
        appStore.notify(`步骤「${pipelineSteps.value[i].label}」出错: ${e.message}`, 'error')
        break
      }
    }

    if (!pipelineResult.value && !userStoppedPipeline.value) {
      pipelineResult.value = { ok: true }
      appStore.notify('日报流水线执行完成', 'success')
    }
    if (!pipelineResult.value && userStoppedPipeline.value) {
      pipelineResult.value = { ok: false, cancelled: true }
    }
  } finally {
    pipelineRunning.value = false
    pipelineAbort.value = null
    loadData()
  }
}

async function runScanOnly() {
  appStore.notify('开始雷达扫描（auto，最多 100 账号）...', 'info', 8000)
  try {
    await api.runScan()
    appStore.notify('扫描完成', 'success')
    loadData()
  } catch (e) {
    appStore.notify('扫描失败: ' + e.message, 'error')
  }
}

async function runBestTimeAnalysis() {
  if (bestTimeRunning.value) return
  bestTimeRunning.value = true
  appStore.notify('开始估算最佳发帖时间...', 'info', 5000)
  try {
    const result = await api.runBestTimeAnalysis()
    if (result.ok) {
      bestTimeAnalysis.value = result.analysis || null
      loadData()
    } else {
      appStore.notify('估算失败: ' + (result.stderr_tail || '未生成分析结果'), 'error')
    }
  } catch (e) {
    appStore.notify('估算失败: ' + e.message, 'error')
  } finally {
    bestTimeRunning.value = false
  }
}

async function installScheduler() {
  installing.value = true
  try {
    const result = await api.installScheduler(installTime.value)
    if (result.ok) {
      appStore.notify(result.message || '调度器安装成功', 'success')
      showInstallModal.value = false
      await loadData()
    } else {
      appStore.notify(result.error || '安装失败', 'error')
    }
  } catch (e) {
    appStore.notify('安装失败: ' + e.message, 'error')
  } finally {
    installing.value = false
  }
}

async function uninstallScheduler() {
  if (!confirm('确定要卸载定时任务吗？')) return
  try {
    const result = await api.uninstallScheduler()
    if (result.ok) {
      appStore.notify(result.message || '调度器已卸载', 'success')
      await loadData()
    } else {
      appStore.notify(result.error || '卸载失败', 'error')
    }
  } catch (e) {
    appStore.notify('卸载失败: ' + e.message, 'error')
  }
}

async function runSchedulerNow() {
  schedulerRunning.value = true
  appStore.notify('开始执行定时任务...', 'info')
  try {
    const result = await api.runSchedulerNow()
    if (result.ok) {
      appStore.notify('定时任务执行完成', 'success')
      await loadData()
    } else {
      appStore.notify('执行失败: ' + (result.error || '未知错误'), 'error')
    }
  } catch (e) {
    appStore.notify('执行失败: ' + e.message, 'error')
  } finally {
    schedulerRunning.value = false
  }
}

async function loadSchedulerLogs() {
  try {
    const result = await api.getSchedulerLogs(50)
    if (result.ok) {
      schedulerLogs.value = result
    }
  } catch (e) {
    appStore.notify('加载日志失败: ' + e.message, 'error')
  }
}

async function toggleLogs() {
  showLogs.value = !showLogs.value
  if (showLogs.value && !schedulerLogs.value) {
    await loadSchedulerLogs()
  }
}

function formatLastRun(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split(' ')
  if (parts.length >= 4) {
    return `${parts[0]} ${parts[1]} ${parts[2]} ${parts[3]}`
  }
  return dateStr
}

import { onUnmounted, onDeactivated } from 'vue'

function startTimer() {
  if (timer) return
  timer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(() => {
  loadData()
  startTimer()
})
onActivated(() => {
  loadData()
  startTimer()
})
onDeactivated(stopTimer)
onUnmounted(stopTimer)
</script>

<style scoped>
.page {
  width: 100%;
  min-height: 100%;
  box-sizing: border-box;
  padding: 32px 40px;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  gap: 16px;
  flex-wrap: wrap;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
  max-width: min(100%, 420px);
}
.pipeline-hint {
  flex: 1 1 100%;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.45;
  margin: 0;
  text-align: right;
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

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  min-height: 24px;
}
.stats-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.update-time {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 500;
}
.btn-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  padding: 0;
}
.btn-icon:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-icon svg.spinning {
  animation: spin 1s linear infinite;
}

/* Grouped Stats Cards */
.stats-grid-grouped {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.focus-grid > .card {
  height: 100%;
}

.card-eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-blue);
}

.focus-actions-card .card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.focus-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.focus-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-primary);
  text-align: left;
  transition: border-color var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
}

.focus-action:hover:not(:disabled) {
  border-color: rgba(59, 130, 246, 0.28);
  background: rgba(59, 130, 246, 0.05);
  transform: translateY(-1px);
}

.focus-action:disabled {
  cursor: wait;
  opacity: 0.72;
}

.focus-action-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.focus-action-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.focus-action-desc {
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--text-tertiary);
}

.focus-action-cta {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent-blue);
}

.activity-card {
  display: flex;
  flex-direction: column;
}

.activity-card-header {
  align-items: flex-start;
  gap: 14px;
}

.activity-card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.activity-refresh {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.timeline-list {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: 14px;
}

.timeline-item:last-child .timeline-line {
  opacity: 0;
}

.timeline-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
  flex-shrink: 0;
}

.timeline-marker {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 4px;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-default);
}

.timeline-marker span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.9;
}

.timeline-marker-done {
  color: var(--accent-green);
  border-color: rgba(52, 199, 89, 0.35);
  background: rgba(52, 199, 89, 0.1);
}

.timeline-marker-pending {
  color: var(--text-tertiary);
  border-color: var(--border-default);
  background: var(--bg-tertiary);
}

.timeline-marker-running {
  color: var(--accent-blue);
  border-color: rgba(59, 130, 246, 0.36);
  background: rgba(59, 130, 246, 0.12);
}

.timeline-marker-attention {
  color: var(--accent-amber);
  border-color: rgba(245, 158, 11, 0.36);
  background: rgba(245, 158, 11, 0.12);
}

.timeline-marker-positive {
  color: var(--accent-green);
  border-color: rgba(52, 199, 89, 0.36);
  background: rgba(52, 199, 89, 0.12);
}

.timeline-line {
  width: 2px;
  flex: 1;
  margin: 6px 0;
  background: linear-gradient(180deg, var(--border-default), transparent);
}

.timeline-body {
  flex: 1;
  min-width: 0;
  padding: 0 0 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.timeline-item:last-child .timeline-body {
  padding-bottom: 0;
  border-bottom: none;
}

.timeline-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.timeline-kicker {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.timeline-time {
  font-size: 11px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.timeline-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.timeline-copy {
  min-width: 0;
}

.timeline-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.timeline-detail {
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-secondary);
}

.timeline-action {
  flex-shrink: 0;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 700;
  transition: border-color var(--transition-fast), background var(--transition-fast), color var(--transition-fast), transform var(--transition-fast);
}

.timeline-action:hover {
  border-color: rgba(59, 130, 246, 0.28);
  background: rgba(59, 130, 246, 0.06);
  color: var(--accent-blue);
  transform: translateY(-1px);
}

.stat-group-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  transition: all var(--transition-fast);
}
.stat-group-card:hover {
  border-color: var(--border-default);
}
.stat-group-card.clickable {
  cursor: pointer;
}
.stat-group-card.clickable:hover {
  border-color: var(--accent-blue);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.stat-group-card-horizontal {
  flex-direction: row;
  gap: 20px;
}

.group-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.group-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.group-icon-blue { background: rgba(59, 130, 246, 0.12); color: var(--accent-blue); }
.group-icon-red { background: var(--accent-red-dim); color: var(--accent-red); }
.group-icon-orange { background: rgba(249, 115, 22, 0.12); color: #f97316; }
.group-icon-cyan { background: rgba(14, 165, 233, 0.12); color: #0284c7; }

.group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.group-badge {
  margin-left: auto;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
}
.group-badge.badge-positive {
  color: var(--accent-green);
  background: var(--accent-green-dim);
}
.group-badge.badge-negative {
  color: var(--accent-red);
  background: var(--accent-red-dim);
}
.group-badge.badge-neutral {
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
}

.group-main {
  margin-bottom: 12px;
}
.group-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}
.group-value.large {
  font-size: 28px;
}
.group-value.best-time-value {
  font-size: 20px;
  line-height: 1.15;
  white-space: nowrap;
}
.group-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.best-time-reason {
  margin-top: 8px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-tertiary);
}

.best-time-card {
  width: 100%;
  text-align: left;
  color: var(--text-primary);
  font: inherit;
}

.best-time-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
  font-size: 11px;
  line-height: 1.35;
  color: var(--text-tertiary);
}

.best-time-meta span:last-child {
  flex-shrink: 0;
  font-weight: 700;
  color: var(--accent-blue);
}

.group-trend {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.group-trend-right {
  margin-top: 0;
  padding-top: 0;
  padding-left: 20px;
  border-top: none;
  border-left: 1px solid var(--border-subtle);
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.group-trend-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.group-trend-label,
.group-trend-range {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.group-trend-chart {
  display: block;
  width: 100%;
  height: 60px;
  transition: opacity var(--transition-fast);
}

.group-trend-chart:hover {
  opacity: 0.9;
}

.group-trend-baseline {
  stroke: var(--border-subtle);
  stroke-width: 1;
  opacity: 0.5;
}

.group-trend-line {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: stroke-width var(--transition-fast);
}

.stat-group-card:hover .group-trend-line {
  stroke-width: 3;
}

.group-trend-line-followers {
  stroke: var(--accent-blue);
}

.group-trend-line-activity {
  stroke: #f97316;
}

.group-trend-dot {
  fill: var(--bg-secondary);
  stroke-width: 2.5;
  transition: r var(--transition-fast);
}

.stat-group-card:hover .group-trend-dot {
  r: 3.5;
}

.group-trend-dot-followers {
  stroke: var(--accent-blue);
}

.group-trend-dot-activity {
  stroke: #f97316;
}

.group-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}
.group-stat {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.group-stat .stat-num {
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.group-stat .stat-text {
  font-size: 11px;
  color: var(--text-tertiary);
}
.group-stat-divider {
  width: 1px;
  height: 16px;
  background: var(--border-subtle);
}

.group-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 8px;
}

.pipeline-card {
  margin-bottom: 24px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-header h3 {
  font-size: 15px;
  font-weight: 600;
}
.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.pipeline-step {
  display: flex;
  gap: 14px;
  padding: 4px 0;
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 28px;
  flex-shrink: 0;
}
.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  border: 2px solid var(--border-default);
  transition: all var(--transition-fast);
}
.step-pending .step-dot {
  border-color: var(--border-default);
}
.step-running .step-dot {
  border-color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.12);
  color: var(--accent-blue);
}
.step-done .step-dot {
  border-color: var(--accent-green);
  background: var(--accent-green);
  color: #fff;
}
.step-error .step-dot {
  border-color: var(--accent-red);
  background: var(--accent-red);
  color: #fff;
}

.step-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid transparent;
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.step-line {
  width: 2px;
  flex: 1;
  min-height: 16px;
  background: var(--border-default);
  margin: 4px 0;
}
.step-done + .pipeline-step .step-line,
.step-done .step-line {
  background: var(--accent-green);
}

.step-content {
  padding: 4px 0 16px;
}
.step-name {
  font-size: 13px;
  font-weight: 600;
}
.step-time {
  font-size: 11px;
  font-weight: 500;
  color: var(--accent-blue);
  font-variant-numeric: tabular-nums;
}
.step-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}
.step-estimate {
  font-size: 11px;
  opacity: 0.7;
}
.step-number {
  font-size: 11px;
}

@media (max-width: 1100px) {
  .stats-grid-grouped { grid-template-columns: 1fr 1fr; }
  .focus-grid { grid-template-columns: 1fr; }
  .timeline-main { flex-direction: column; }
}
@media (max-width: 700px) {
  .stats-grid-grouped { grid-template-columns: 1fr; }
  .timeline-action { width: 100%; justify-content: center; }
  .scheduler-bar { flex-direction: column; align-items: flex-start; gap: 10px; }
  .stat-group-card-horizontal {
    flex-direction: column;
  }
  .group-trend-right {
    padding-left: 0;
    padding-top: 12px;
    border-left: none;
    border-top: 1px solid var(--border-subtle);
    min-width: auto;
  }
}

/* Scheduler Bar (compact mode when installed) */
.scheduler-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-top: 24px;
}
.scheduler-bar-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.scheduler-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-green);
  box-shadow: 0 0 6px var(--accent-green);
}
.scheduler-bar-text {
  font-size: 13px;
  color: var(--text-secondary);
}
.scheduler-last-run {
  color: var(--text-tertiary);
}
.scheduler-bar-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
.btn-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast);
}
.btn-link:hover {
  color: var(--accent-blue);
}
.btn-link.primary {
  color: var(--accent-blue);
  font-weight: 600;
}
.btn-link.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-link.danger:hover {
  color: var(--accent-red);
}

.scheduler-logs-standalone {
  margin-top: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px;
}

.scheduler-card {
  margin-top: 24px;
}

.scheduler-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.info-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.scheduler-empty {
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.scheduler-empty p {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.scheduler-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.scheduler-logs {
  margin-top: 16px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.logs-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.logs-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--text-primary);
  transition: all var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-blue);
  background: var(--bg-secondary);
}

.form-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 8px;
  line-height: 1.5;
}

.badge-gray {
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}
</style>
