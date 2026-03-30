<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">粉丝统计</h1>
        <p class="page-subtitle" v-if="username">@{{ username }}</p>
      </div>
      <div class="header-actions">
        <button
          class="btn btn-primary"
          @click="fetchNow"
          :disabled="fetching"
        >
          <svg v-if="!fetching" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
          <span v-if="fetching" class="btn-spinner"></span>
          {{ fetching ? '采集中...' : '采集最新数据' }}
        </button>
      </div>
    </header>

    <!-- Stats Cards -->
    <div class="stats-grid" v-if="latestRecord">
      <div class="stat-card stat-followers">
        <div class="stat-icon-wrap">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ latestRecord.followers }}</div>
          <div class="stat-label">Followers</div>
        </div>
        <div class="stat-change" v-if="followerChange !== null" :class="changeClass">
          {{ followerChange > 0 ? '+' : '' }}{{ followerChange }}
        </div>
      </div>
      <div class="stat-card stat-following">
        <div class="stat-icon-wrap following">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ latestRecord.following }}</div>
          <div class="stat-label">Following</div>
        </div>
      </div>
      <div class="stat-card stat-records">
        <div class="stat-icon-wrap records">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 20V10M18 20V4M6 20v-4"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ records.length }}</div>
          <div class="stat-label">天数据</div>
        </div>
      </div>
      <div class="stat-card stat-date">
        <div class="stat-icon-wrap date">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ latestRecord.date }}</div>
          <div class="stat-label">最新数据</div>
        </div>
      </div>
    </div>

    <!-- Chart -->
    <div class="card chart-card" v-if="records.length >= 2">
      <div class="card-header">
        <h3>粉丝趋势</h3>
        <span class="chart-range">共 {{ records.length }} 天</span>
      </div>
      <div class="chart-container">
        <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="trend-chart">
          <!-- Grid lines -->
          <line v-for="y in gridLinesY" :key="'g'+y.val"
            :x1="chartPadLeft" :y1="y.y" :x2="chartWidth - chartPadRight" :y2="y.y"
            class="grid-line" />
          <!-- Y axis labels -->
          <text v-for="y in gridLinesY" :key="'l'+y.val"
            :x="chartPadLeft - 8" :y="y.y + 4" class="axis-label" text-anchor="end">{{ y.val }}</text>
          <!-- X axis labels -->
          <text v-for="(label, i) in xLabels" :key="'x'+i"
            :x="label.x" :y="chartHeight - 4" class="axis-label" text-anchor="middle">{{ label.text }}</text>
          <!-- Area fill -->
          <path :d="areaPath" class="chart-area" />
          <!-- Line -->
          <path :d="linePath" class="chart-line" />
          <!-- Data points -->
          <circle v-for="(pt, i) in chartPoints" :key="'p'+i"
            :cx="pt.x" :cy="pt.y" r="3.5" class="chart-dot"
            @mouseenter="hoverPoint = pt" @mouseleave="hoverPoint = null" />
        </svg>
        <!-- Tooltip -->
        <div class="chart-tooltip" v-if="hoverPoint"
          :style="{ left: tooltipLeft + 'px', top: tooltipTop + 'px' }">
          <div class="tooltip-date">{{ hoverPoint.date }}</div>
          <div class="tooltip-value">👥 {{ hoverPoint.value }} followers</div>
          <div class="tooltip-change" v-if="hoverPoint.change !== undefined" :class="hoverPoint.change > 0 ? 'up' : hoverPoint.change < 0 ? 'down' : ''">
            {{ hoverPoint.change > 0 ? '+' : '' }}{{ hoverPoint.change }}
          </div>
        </div>
      </div>
    </div>

    <!-- Records Table -->
    <div class="card" v-if="records.length">
      <div class="card-header">
        <h3>历史记录</h3>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th class="num">Followers</th>
              <th class="num">变化</th>
              <th class="num">Following</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in tableRows" :key="row.date">
              <td class="date-cell">{{ row.date }}</td>
              <td class="num">{{ row.followers }}</td>
              <td class="num">
                <span v-if="row.diff !== null" :class="diffClass(row.diff)">
                  {{ row.diff > 0 ? '+' : '' }}{{ row.diff }}
                </span>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="num">{{ row.following }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty state -->
    <div class="card empty-state" v-if="!loading && !records.length">
      <svg class="empty-icon" width="80" height="80" viewBox="0 0 80 80" fill="none">
        <circle cx="40" cy="40" r="38" stroke="currentColor" stroke-width="2" stroke-dasharray="4 4" opacity="0.2"/>
        <path d="M28 50v-4a8 8 0 0 1 8-8h8a8 8 0 0 1 8 8v4" stroke="currentColor" stroke-width="2" opacity="0.4"/>
        <circle cx="40" cy="28" r="6" stroke="currentColor" stroke-width="2" opacity="0.4"/>
      </svg>
      <p class="empty-title">还没有粉丝数据</p>
      <p class="empty-hint">点击"采集最新数据"获取第一条记录</p>
      <button class="btn btn-primary btn-sm" @click="fetchNow" :disabled="fetching" style="margin-top: 12px;">
        {{ fetching ? '采集中...' : '开始采集' }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div class="stats-grid" v-if="loading && !records.length">
      <div class="stat-card skeleton" v-for="i in 4" :key="i">
        <div class="skeleton-bar" style="width: 60%; height: 20px"></div>
        <div class="skeleton-bar" style="width: 40%; height: 14px; margin-top: 8px"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const appStore = useAppStore()
const loading = ref(false)
const fetching = ref(false)
const username = ref('')
const records = ref([])
const hoverPoint = ref(null)

// Chart dimensions
const chartWidth = 720
const chartHeight = 280
const chartPadLeft = 50
const chartPadRight = 20
const chartPadTop = 20
const chartPadBottom = 30

async function loadData() {
  loading.value = true
  try {
    const data = await api.getFollowers()
    username.value = data.username || ''
    records.value = (data.records || []).sort((a, b) => a.date.localeCompare(b.date))
  } catch (e) {
    appStore.notify('加载粉丝数据失败: ' + e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function fetchNow() {
  fetching.value = true
  appStore.notify('正在采集粉丝数据...', 'info', 8000)
  try {
    const result = await api.fetchFollowers(username.value || 'jackaiwison')
    if (result.ok) {
      appStore.notify(`采集完成: ${result.followers} followers`, 'success')
      await loadData()
    } else {
      appStore.notify('采集失败: ' + (result.error || '未知错误'), 'error')
    }
  } catch (e) {
    appStore.notify('采集失败: ' + e.message, 'error')
  } finally {
    fetching.value = false
  }
}

// Computed
const latestRecord = computed(() => records.value.length ? records.value[records.value.length - 1] : null)

const followerChange = computed(() => {
  if (records.value.length < 2) return null
  const curr = records.value[records.value.length - 1]
  const prev = records.value[records.value.length - 2]
  if (curr.followers < 0 || prev.followers < 0) return null
  return curr.followers - prev.followers
})

const changeClass = computed(() => {
  const c = followerChange.value
  if (c === null) return ''
  return c > 0 ? 'change-up' : c < 0 ? 'change-down' : 'change-same'
})

const tableRows = computed(() => {
  const rows = []
  const sorted = [...records.value].reverse()
  for (let i = 0; i < sorted.length; i++) {
    const r = sorted[i]
    const prev = sorted[i + 1]
    rows.push({
      ...r,
      diff: prev && r.followers >= 0 && prev.followers >= 0 ? r.followers - prev.followers : null,
    })
  }
  return rows
})

function diffClass(diff) {
  if (diff > 0) return 'diff-up'
  if (diff < 0) return 'diff-down'
  return 'diff-same'
}

// Chart computations
const chartPoints = computed(() => {
  const data = records.value.filter(r => r.followers >= 0)
  if (data.length < 2) return []

  const vals = data.map(r => r.followers)
  const minVal = Math.min(...vals)
  const maxVal = Math.max(...vals)
  const range = maxVal - minVal || 1
  const yPad = range * 0.1

  const plotW = chartWidth - chartPadLeft - chartPadRight
  const plotH = chartHeight - chartPadTop - chartPadBottom

  return data.map((r, i) => {
    const x = chartPadLeft + (i / (data.length - 1)) * plotW
    const y = chartPadTop + plotH - ((r.followers - minVal + yPad) / (range + yPad * 2)) * plotH
    const prev = i > 0 ? data[i - 1].followers : undefined
    return {
      x, y,
      date: r.date,
      value: r.followers,
      change: prev !== undefined ? r.followers - prev : undefined,
    }
  })
})

const linePath = computed(() => {
  if (chartPoints.value.length < 2) return ''
  return chartPoints.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
})

const areaPath = computed(() => {
  const pts = chartPoints.value
  if (pts.length < 2) return ''
  const bottom = chartHeight - chartPadBottom
  return `M ${pts[0].x} ${bottom} ` +
    pts.map(p => `L ${p.x} ${p.y}`).join(' ') +
    ` L ${pts[pts.length - 1].x} ${bottom} Z`
})

const gridLinesY = computed(() => {
  const data = records.value.filter(r => r.followers >= 0)
  if (data.length < 2) return []
  const vals = data.map(r => r.followers)
  const minVal = Math.min(...vals)
  const maxVal = Math.max(...vals)
  const range = maxVal - minVal || 1
  const yPad = range * 0.1
  const plotH = chartHeight - chartPadTop - chartPadBottom
  const lines = []
  const step = Math.max(1, Math.ceil(range / 4))
  const start = Math.floor(minVal / step) * step
  for (let v = start; v <= maxVal + step; v += step) {
    const y = chartPadTop + plotH - ((v - minVal + yPad) / (range + yPad * 2)) * plotH
    if (y >= chartPadTop && y <= chartHeight - chartPadBottom) {
      lines.push({ y, val: v })
    }
  }
  return lines
})

const xLabels = computed(() => {
  const data = records.value.filter(r => r.followers >= 0)
  if (data.length < 2) return []
  const plotW = chartWidth - chartPadLeft - chartPadRight
  const maxLabels = Math.min(data.length, 7)
  const step = Math.max(1, Math.floor((data.length - 1) / (maxLabels - 1)))
  const labels = []
  for (let i = 0; i < data.length; i += step) {
    const x = chartPadLeft + (i / (data.length - 1)) * plotW
    labels.push({ x, text: data[i].date.slice(5) }) // MM-DD
  }
  // Always include last
  const last = data.length - 1
  if (labels.length === 0 || labels[labels.length - 1].text !== data[last].date.slice(5)) {
    labels.push({ x: chartPadLeft + plotW, text: data[last].date.slice(5) })
  }
  return labels
})

const tooltipLeft = computed(() => {
  if (!hoverPoint.value) return 0
  const svgEl = document.querySelector('.trend-chart')
  if (!svgEl) return 0
  const rect = svgEl.getBoundingClientRect()
  const scale = rect.width / chartWidth
  return hoverPoint.value.x * scale + 12
})

const tooltipTop = computed(() => {
  if (!hoverPoint.value) return 0
  const svgEl = document.querySelector('.trend-chart')
  if (!svgEl) return 0
  const rect = svgEl.getBoundingClientRect()
  const scale = rect.height / chartHeight
  return hoverPoint.value.y * scale - 10
})

onMounted(loadData)
onActivated(loadData)
</script>

<style scoped>
.page {
  padding: 32px 40px;
  max-width: 1000px;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  gap: 16px;
  flex-wrap: wrap;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
}
.page-subtitle {
  color: var(--accent-blue);
  font-size: 13px;
  margin-top: 4px;
  font-weight: 500;
}

/* Stats Grid */
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
  position: relative;
}
.stat-card:hover {
  border-color: var(--border-default);
}
.stat-icon-wrap {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(59, 130, 246, 0.1);
  color: var(--accent-blue);
}
.stat-icon-wrap.following {
  background: var(--accent-green-dim);
  color: var(--accent-green);
}
.stat-icon-wrap.records {
  background: var(--accent-purple-dim);
  color: var(--accent-purple);
}
.stat-icon-wrap.date {
  background: var(--accent-amber-dim);
  color: var(--accent-amber);
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}
.stat-change {
  position: absolute;
  top: 12px;
  right: 14px;
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding: 2px 8px;
  border-radius: 20px;
}
.change-up {
  color: #10B981;
  background: rgba(16, 185, 129, 0.1);
}
.change-down {
  color: #EF4444;
  background: rgba(239, 68, 68, 0.1);
}
.change-same {
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
}

/* Chart */
.chart-card {
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
.chart-range {
  font-size: 12px;
  color: var(--text-tertiary);
}
.chart-container {
  position: relative;
  width: 100%;
  overflow: hidden;
}
.trend-chart {
  width: 100%;
  height: auto;
}
.grid-line {
  stroke: var(--border-subtle);
  stroke-width: 1;
  stroke-dasharray: 4 4;
}
.axis-label {
  font-size: 10px;
  fill: var(--text-tertiary);
  font-family: var(--font-mono);
}
.chart-line {
  fill: none;
  stroke: var(--accent-blue);
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.chart-area {
  fill: url(#areaGrad);
  opacity: 0.15;
  fill: rgba(59, 130, 246, 0.12);
}
.chart-dot {
  fill: var(--bg-secondary);
  stroke: var(--accent-blue);
  stroke-width: 2;
  cursor: pointer;
  transition: r 0.15s;
}
.chart-dot:hover {
  r: 5.5;
  fill: var(--accent-blue);
}
.chart-tooltip {
  position: absolute;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 12px;
  box-shadow: var(--shadow-md);
  pointer-events: none;
  z-index: 10;
  white-space: nowrap;
}
.tooltip-date {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.tooltip-value {
  color: var(--text-secondary);
}
.tooltip-change.up { color: #10B981; font-weight: 600; }
.tooltip-change.down { color: #EF4444; font-weight: 600; }

/* Table */
.table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 10px 12px;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  border-bottom: 1px solid var(--border-subtle);
}
.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  font-variant-numeric: tabular-nums;
}
.data-table th.num,
.data-table td.num {
  text-align: right;
}
.date-cell {
  font-family: var(--font-mono);
  font-weight: 500;
}
.diff-up {
  color: #10B981;
  font-weight: 600;
}
.diff-down {
  color: #EF4444;
  font-weight: 600;
}
.diff-same {
  color: var(--text-tertiary);
}
.text-muted {
  color: var(--text-tertiary);
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 60px 16px;
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
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 4px;
}
.empty-hint {
  font-size: 12px;
  margin: 0;
  opacity: 0.8;
}

/* Button spinner */
.btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 4px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Skeleton */
.skeleton {
  animation: pulse 1.5s ease-in-out infinite;
}
.skeleton-bar {
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 500px) {
  .stats-grid { grid-template-columns: 1fr; }
  .page { padding: 20px 16px; }
}
</style>
