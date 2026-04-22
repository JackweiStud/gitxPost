<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">概览</h1>
        <p class="page-subtitle">gitxPost 工作台</p>
      </div>
      <div class="header-actions">
        <p v-if="pipelineRunning" class="pipeline-hint">
          全流程约 5–15 分钟（视网络与账号量）。重复点击不会并行执行；可随时点「停止」。
        </p>
        <button
          v-if="pipelineRunning"
          type="button"
          class="btn btn-danger btn-lg"
          @click="stopPipeline"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>
          停止
        </button>
        <button class="btn btn-primary btn-lg" @click="runFullPipeline" :disabled="pipelineRunning">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          {{ pipelineRunning ? '执行中...' : '一键跑日报' }}
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

    <!-- Stats Grid - 3 Group Cards -->
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
      <div class="stat-group-card clickable" @click="$router.push('/followers')">
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

      <!-- 内容生产 -->
      <div class="stat-group-card clickable" @click="$router.push('/followers')">
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

    <!-- Quick Actions + Latest Report -->
    <div class="two-col">
      <div class="card">
        <div class="card-header">
          <h3>快捷操作</h3>
        </div>
        <div class="action-list">
          <button class="action-item" @click="$router.push('/radar')">
            <div class="action-icon action-icon-blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
            </div>
            <div class="action-body">
              <div class="action-name">查看日报</div>
              <div class="action-desc">浏览 AI 生成的每日推文精选</div>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
          </button>
          <button class="action-item" @click="$router.push('/reply')">
            <div class="action-icon action-icon-green">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </div>
            <div class="action-body">
              <div class="action-name">回帖工作台</div>
              <div class="action-desc">AI 辅助回复感兴趣的推文</div>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
          </button>
          <button class="action-item" @click="$router.push('/followers')">
            <div class="action-icon action-icon-red">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            <div class="action-body">
              <div class="action-name">粉丝统计</div>
              <div class="action-desc">查看粉丝增长与活动趋势</div>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
          </button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>最近日报</h3>
          <router-link to="/radar" class="card-link">查看全部</router-link>
        </div>
        <div class="report-list" v-if="reports.length">
          <router-link
            v-for="r in reports.slice(0, 5)"
            :key="r.date"
            :to="'/radar?date=' + r.date"
            class="report-item"
          >
            <div class="report-date">{{ r.date }}</div>
            <div class="report-size">{{ (r.size / 1024).toFixed(1) }}KB</div>
          </router-link>
        </div>
        <div class="empty-state" v-else>
          <svg class="empty-icon" width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="40" cy="40" r="38" stroke="currentColor" stroke-width="2" stroke-dasharray="4 4" opacity="0.2"/>
            <path d="M25 40h30M40 25v30" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" opacity="0.3"/>
            <circle cx="40" cy="40" r="12" stroke="currentColor" stroke-width="2" opacity="0.4"/>
            <path d="M40 34v6l3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>
          </svg>
          <p class="empty-title">还没有日报</p>
          <p class="empty-hint">点击下方按钮开始生成第一份日报</p>
          <button class="btn btn-primary btn-sm" @click="runFullPipeline" style="margin-top: 12px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            一键跑日报
          </button>
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
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const appStore = useAppStore()
const status = ref(null)
const reports = ref([])
const followers = ref(null)
const pipelineRunning = ref(false)
const pipelineResult = ref(null)
const pipelineAbort = ref(null)
const userStoppedPipeline = ref(false)
const lastUpdateTime = ref(null)
const isRefreshing = ref(false)
const now = ref(Date.now())
let timer = null

// Scheduler state
const schedulerStatus = ref(null)
const showInstallModal = ref(false)
const installTime = ref('09:00')
const installing = ref(false)
const schedulerRunning = ref(false)
const showLogs = ref(false)
const schedulerLogs = ref(null)

const pipelineSteps = ref([
  { id: 'scan', label: '雷达扫描', desc: '抓取 230+ 账号最新推文', estimate: '3-8 分钟', status: 'pending', startTime: null, duration: null },
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
const followersData = computed(() => {
  if (!followers.value?.records || followers.value.records.length === 0) {
    return { count: '--', change: 0, changeText: '', activity: '--' }
  }
  
  const records = [...followers.value.records].sort((a, b) => a.date.localeCompare(b.date))
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

async function loadData() {
  if (isRefreshing.value) return
  isRefreshing.value = true
  try {
    const [s, r, f, sched] = await Promise.all([
      api.getStatus(), 
      api.getReports(),
      api.getFollowers(),
      api.getSchedulerStatus()
    ])
    status.value = s
    reports.value = r.reports || []
    followers.value = f
    schedulerStatus.value = sched
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
  appStore.notify('开始雷达扫描...', 'info', 8000)
  try {
    await api.runScan()
    appStore.notify('扫描完成', 'success')
    loadData()
  } catch (e) {
    appStore.notify('扫描失败: ' + e.message, 'error')
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
  padding: 32px 40px;
  max-width: 1200px;
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
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-group-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
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
.group-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
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

/* Action icon colors */
.action-icon-red { background: var(--accent-red-dim); color: var(--accent-red); }

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
.card-link {
  font-size: 12px;
  color: var(--text-tertiary);
}
.card-link:hover {
  color: var(--accent-blue);
  text-decoration: none;
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

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  width: 100%;
  transition: background var(--transition-fast);
}
.action-item:hover {
  background: var(--bg-hover);
}
.action-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.action-icon-blue { background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); }
.action-icon-green { background: var(--accent-green-dim); color: var(--accent-green); }
.action-icon-amber { background: var(--accent-amber-dim); color: var(--accent-amber); }

.action-body { flex: 1; }
.action-name {
  font-size: 13px;
  font-weight: 600;
}
.action-desc {
  font-size: 11.5px;
  color: var(--text-tertiary);
  margin-top: 1px;
}
.action-item > svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.report-list {
  display: flex;
  flex-direction: column;
}
.report-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  text-decoration: none;
  transition: background var(--transition-fast);
}
.report-item:hover {
  background: var(--bg-hover);
  text-decoration: none;
}
.report-date {
  font-size: 13px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.report-size {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.empty-state {
  text-align: center;
  padding: 40px 16px;
  color: var(--text-tertiary);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.empty-icon {
  color: var(--text-tertiary);
  margin-bottom: 16px;
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

@media (max-width: 1100px) {
  .stats-grid-grouped { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 700px) {
  .stats-grid-grouped { grid-template-columns: 1fr; }
  .two-col { grid-template-columns: 1fr; }
  .scheduler-bar { flex-direction: column; align-items: flex-start; gap: 10px; }
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
