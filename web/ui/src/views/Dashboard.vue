<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">概览</h1>
        <p class="page-subtitle">gitxPost 工作台</p>
      </div>
      <div class="header-actions">
        <p v-if="pipelineRunning" class="pipeline-hint">
          全流程约 5–20 分钟（视网络与账号量）。重复点击不会并行执行；可随时点「停止」。
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

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon stat-icon-blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ status?.scan?.last_scan_time || '--' }}</div>
          <div class="stat-label">最近扫描</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-green">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ status?.scan?.total_accounts || 0 }}</div>
          <div class="stat-label">监控账号</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-amber">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ status?.scan?.new_tweets || 0 }}</div>
          <div class="stat-label">新推文</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-purple">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ status?.scan?.new_originals || 0 }}</div>
          <div class="stat-label">原创帖</div>
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
            <div class="step-name">{{ step.label }}</div>
            <div class="step-desc">{{ step.desc }}</div>
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
          <button class="action-item" @click="runScanOnly">
            <div class="action-icon action-icon-amber">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </div>
            <div class="action-body">
              <div class="action-name">仅扫描</div>
              <div class="action-desc">只运行雷达扫描，不生成日报</div>
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
          <p>暂无日报数据</p>
          <p class="empty-hint">运行「一键跑日报」生成第一份</p>
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
const pipelineRunning = ref(false)
const pipelineResult = ref(null)
const pipelineAbort = ref(null)
const userStoppedPipeline = ref(false)
const lastUpdateTime = ref(null)
const isRefreshing = ref(false)
const now = ref(Date.now())
let timer = null

const pipelineSteps = ref([
  { id: 'scan', label: '雷达扫描', desc: '抓取 230+ 账号最新推文', status: 'pending' },
  { id: 'analyze', label: '数据分析', desc: '聚类分析近 7 天数据', status: 'pending' },
  { id: 'daily', label: '生成日报', desc: 'AI 筛选并生成 Markdown 日报', status: 'pending' },
])

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

async function loadData() {
  if (isRefreshing.value) return
  isRefreshing.value = true
  try {
    const [s, r] = await Promise.all([api.getStatus(), api.getReports()])
    status.value = s
    reports.value = r.reports || []
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
  pipelineSteps.value.forEach((s) => (s.status = 'pending'))

  const stepFns = [() => api.runScan(sig), () => api.runAnalyze(7, sig), () => api.runDaily(sig)]

  try {
    for (let i = 0; i < stepFns.length; i++) {
      if (userStoppedPipeline.value) {
        pipelineSteps.value[i].status = 'pending'
        break
      }
      pipelineSteps.value[i].status = 'running'
      try {
        const result = await stepFns[i]()
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 18px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  transition: border-color var(--transition-fast);
}
.stat-card:hover {
  border-color: var(--border-default);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon-blue { background: rgba(59, 130, 246, 0.12); color: var(--accent-blue); }
.stat-icon-green { background: var(--accent-green-dim); color: var(--accent-green); }
.stat-icon-amber { background: var(--accent-amber-dim); color: var(--accent-amber); }
.stat-icon-purple { background: var(--accent-purple-dim); color: var(--accent-purple); }

.stat-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
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
.step-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
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
  padding: 28px 16px;
  color: var(--text-tertiary);
  font-size: 13px;
}
.empty-hint {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.7;
}

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .two-col { grid-template-columns: 1fr; }
}
</style>
