<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">回帖工作台</h1>
        <p class="page-subtitle">提取推文 → AI 生成回复 → 确认发送</p>
      </div>
    </header>

    <!-- Step indicator -->
    <div class="steps-bar">
      <div
        v-for="(s, idx) in steps"
        :key="s.id"
        class="step-item"
        :class="{ 
          active: currentStep === idx, 
          done: idx < currentStep,
          clickable: idx < currentStep
        }"
        @click="idx < currentStep && goToStep(idx)"
      >
        <div class="step-badge">{{ idx < currentStep ? '✓' : idx + 1 }}</div>
        <span class="step-label">{{ s.label }}</span>
      </div>
    </div>

    <!-- Step 0: Input URL -->
    <div class="step-panel" v-if="currentStep === 0">
      <div class="card input-card">
        <h3>输入推文链接</h3>
        <p class="input-hint">粘贴 x.com 推文 URL，支持 twitter.com 格式</p>
        <div class="url-input-row">
          <input
            v-model="tweetUrl"
            type="text"
            class="url-input"
            placeholder="https://x.com/username/status/123456789"
            @keydown.enter="extractTweet"
          />
          <button class="btn btn-primary" @click="extractTweet" :disabled="!tweetUrl.trim() || extracting">
            {{ extracting ? '浏览器加载中，请稍候...' : '提取正文' }}
          </button>
        </div>
        <div class="url-examples" v-if="recentUrls.length">
          <span class="examples-label">最近使用:</span>
          <button
            v-for="u in recentUrls.slice(0, 3)"
            :key="u"
            class="example-chip"
            @click="tweetUrl = u"
          >
            {{ truncateUrl(u) }}
          </button>
        </div>

        <div class="extract-progress" v-if="extracting">
          <div class="progress-bar">
            <div class="progress-fill"></div>
          </div>
          <div class="progress-text">Chrome 正在打开推文页面，等待页面渲染完成...</div>
        </div>
      </div>
    </div>

    <!-- Step 1: View extracted tweet + generate replies -->
    <div class="step-panel" v-if="currentStep === 1">
      <div class="card tweet-preview">
        <div class="preview-header">
          <div class="preview-author">
            <div class="preview-avatar">{{ tweetData?.handle?.[0]?.toUpperCase() || '?' }}</div>
            <div>
              <div class="preview-name">{{ tweetData?.handle || '未知' }}</div>
              <div class="preview-lang">{{ tweetData?.lang || '' }}</div>
            </div>
          </div>
          <a :href="tweetUrl" target="_blank" class="preview-link">
            查看原文
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          </a>
        </div>
        <div class="preview-text">{{ tweetData?.text }}</div>
      </div>

      <div class="generate-bar">
        <button class="btn btn-primary btn-lg" @click="generateReplies" :disabled="generatingReplies">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
          {{ generatingReplies ? 'AI 生成中...' : '生成回复备选' }}
        </button>
        <button class="btn btn-ghost" @click="reset">重新开始</button>
      </div>
    </div>

    <!-- Step 2: Select reply -->
    <div class="step-panel" v-if="currentStep === 2">
      <div class="card tweet-preview compact">
        <div class="preview-header">
          <div class="preview-author">
            <div class="preview-avatar sm">{{ tweetData?.handle?.[0]?.toUpperCase() || '?' }}</div>
            <span class="preview-name">{{ tweetData?.handle }}</span>
          </div>
        </div>
        <div class="preview-text sm">{{ truncateText(tweetData?.text, 120) }}</div>
      </div>

      <h3 class="reply-title">选择回复</h3>
      <div class="reply-options">
        <div
          v-for="(text, key) in replies"
          :key="key"
          class="reply-option"
          :class="{ selected: selectedReply === key }"
          @click="selectedReply = key"
        >
          <div class="option-header">
            <span class="option-key">{{ key }}</span>
            <span class="option-type">{{ replyTypeLabel(key) }}</span>
          </div>
          <div class="option-text">{{ text }}</div>
          <div class="option-meta">{{ text.length }} 字符</div>
        </div>
      </div>

      <div class="custom-reply">
        <div class="custom-label">或自定义回复:</div>
        <textarea
          v-model="customReply"
          class="custom-textarea"
          placeholder="输入自定义回复内容..."
          rows="3"
          @input="selectedReply = customReply.trim() ? 'custom' : null"
        ></textarea>
      </div>

      <div class="action-bar">
        <button class="btn btn-ghost" @click="currentStep = 1">返回</button>
        <button class="btn btn-primary btn-lg" @click="confirmReply" :disabled="!finalReplyText">
          确认回复内容
        </button>
      </div>
    </div>

    <!-- Step 3: Confirm & Send -->
    <div class="step-panel" v-if="currentStep === 3">
      <div class="confirm-card card">
        <div class="confirm-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span>即将回复 @{{ tweetData?.handle }}</span>
        </div>
        <div class="confirm-body">
          <div class="confirm-text">{{ finalReplyText }}</div>
          <div class="confirm-meta">{{ finalReplyText?.length || 0 }} / 280 字符</div>
        </div>

        <div class="confirm-actions">
          <button class="btn btn-ghost" @click="currentStep = 2">修改</button>
          <button class="btn btn-ghost" @click="sendDraft" :disabled="sending">
            仅填入（草稿）
          </button>
          <button class="btn btn-primary btn-lg" @click="sendPublish" :disabled="sending">
            {{ sending ? '发送中...' : '确认发送' }}
          </button>
        </div>
      </div>

      <div class="result-card card" v-if="sendResult">
        <div class="result-icon" :class="sendResult.ok ? 'result-ok' : 'result-fail'">
          <svg v-if="sendResult.ok" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </div>
        <div class="result-text">{{ sendResult.ok ? '回复发送成功' : '发送失败' }}</div>
        <div class="result-detail" v-if="!sendResult.ok">{{ sendResult.error || sendResult.stderr }}</div>
        <button class="btn btn-ghost" @click="reset" style="margin-top: 12px;">处理下一条</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app.js'
import * as api from '../api/xpost.js'

const route = useRoute()
const appStore = useAppStore()

const steps = [
  { id: 'url', label: '输入链接' },
  { id: 'extract', label: '查看推文' },
  { id: 'select', label: '选择回复' },
  { id: 'send', label: '确认发送' },
]

const currentStep = ref(0)
const tweetUrl = ref('')
const tweetData = ref(null)
const extracting = ref(false)
const generatingReplies = ref(false)
const replies = ref({})
const selectedReply = ref(null)
const customReply = ref('')
const sending = ref(false)
const sendResult = ref(null)
const recentUrls = ref([])

const finalReplyText = computed(() => {
  if (selectedReply.value === 'custom') return customReply.value.trim()
  if (selectedReply.value && replies.value[selectedReply.value]) {
    return replies.value[selectedReply.value]
  }
  return ''
})

function replyTypeLabel(key) {
  const labels = { A: '追问型', B: '实践型', C: '简短型' }
  return labels[key] || ''
}

function goToStep(step) {
  // 只允许回退到已完成的步骤
  if (step < currentStep.value) {
    currentStep.value = step
  }
}

function truncateUrl(url) {
  const match = url.match(/status\/(\d+)/)
  if (match) return '...' + match[1].slice(-8)
  return url.slice(-20)
}

function truncateText(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function addRecentUrl(url) {
  recentUrls.value = [url, ...recentUrls.value.filter((u) => u !== url)].slice(0, 10)
}

async function extractTweet() {
  if (!tweetUrl.value.trim()) return
  extracting.value = true
  appStore.notify('正在启动浏览器并加载推文页面，网络慢时可能需要 30-60 秒...', 'info', 20000)
  try {
    const data = await api.extractTweet(tweetUrl.value.trim())
    if (data.ok === false) {
      appStore.notify('提取失败: ' + (data.error || '未知错误'), 'error')
      return
    }
    tweetData.value = data
    addRecentUrl(tweetUrl.value.trim())
    currentStep.value = 1
    appStore.notify('推文正文提取成功', 'success')
  } catch (e) {
    appStore.notify('提取推文失败: ' + e.message, 'error')
  } finally {
    extracting.value = false
  }
}

async function generateReplies() {
  if (!tweetData.value?.text) return
  generatingReplies.value = true
  try {
    const data = await api.generateReplies(tweetData.value.text, tweetData.value.handle || '')
    if (data.error) {
      appStore.notify('生成失败: ' + data.error, 'error')
      return
    }
    replies.value = data
    selectedReply.value = null
    customReply.value = ''
    currentStep.value = 2
  } catch (e) {
    appStore.notify('生成回复失败: ' + e.message, 'error')
  } finally {
    generatingReplies.value = false
  }
}

function confirmReply() {
  if (!finalReplyText.value) return
  sendResult.value = null
  currentStep.value = 3
}

async function sendDraft() {
  sending.value = true
  try {
    const data = await api.sendReply(tweetUrl.value, finalReplyText.value, false)
    sendResult.value = { ok: data.ok !== false }
    if (data.ok !== false) appStore.notify('草稿已填入浏览器', 'success')
  } catch (e) {
    sendResult.value = { ok: false, error: e.message }
  } finally {
    sending.value = false
  }
}

async function sendPublish() {
  sending.value = true
  try {
    const data = await api.sendReply(tweetUrl.value, finalReplyText.value, true)
    sendResult.value = { ok: data.ok !== false, ...data }
    if (data.ok !== false) appStore.notify('回复发送成功', 'success')
    else appStore.notify('发送失败', 'error')
  } catch (e) {
    sendResult.value = { ok: false, error: e.message }
    appStore.notify('发送失败: ' + e.message, 'error')
  } finally {
    sending.value = false
  }
}

function reset() {
  currentStep.value = 0
  tweetData.value = null
  replies.value = {}
  selectedReply.value = null
  customReply.value = ''
  sendResult.value = null
  sending.value = false
  tweetUrl.value = ''
}

onMounted(() => {
  const urlParam = route.query.url
  if (urlParam) {
    tweetUrl.value = urlParam
    extractTweet()
  }
})
</script>

<style scoped>
.page {
  padding: 32px 40px;
  max-width: 860px;
}
.page-header {
  margin-bottom: 24px;
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

/* Steps bar */
.steps-bar {
  display: flex;
  gap: 0;
  margin-bottom: 28px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 4px;
}
.step-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-tertiary);
  transition: all var(--transition-fast);
}
.step-item.clickable {
  cursor: pointer;
}
.step-item.clickable:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.step-item.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.step-item.done {
  color: var(--accent-green);
}
.step-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.step-item.active .step-badge {
  background: var(--accent-blue);
  color: #fff;
}
.step-item.done .step-badge {
  background: var(--accent-green);
  color: #fff;
  font-size: 10px;
}
.step-label {
  font-weight: 500;
}

/* Step 0: URL input */
.input-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.input-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 16px;
}
.url-input-row {
  display: flex;
  gap: 10px;
}
.url-input {
  flex: 1;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-mono);
  transition: border-color var(--transition-fast);
}
.url-input:focus {
  border-color: var(--accent-blue);
}
.url-input::placeholder {
  color: var(--text-tertiary);
}
.url-examples {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.examples-label {
  font-size: 11px;
  color: var(--text-tertiary);
}
.example-chip {
  padding: 3px 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: 100px;
  font-size: 11px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  transition: all var(--transition-fast);
}
.example-chip:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

/* Step 1: Tweet preview */
.tweet-preview {
  margin-bottom: 16px;
}
.tweet-preview.compact {
  padding: 14px;
  margin-bottom: 20px;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.preview-author {
  display: flex;
  align-items: center;
  gap: 10px;
}
.preview-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-secondary);
}
.preview-avatar.sm {
  width: 28px;
  height: 28px;
  font-size: 11px;
}
.preview-name {
  font-size: 14px;
  font-weight: 600;
}
.preview-lang {
  font-size: 11px;
  color: var(--text-tertiary);
}
.preview-link {
  font-size: 12px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
}
.preview-link:hover {
  color: var(--accent-blue);
  text-decoration: none;
}
.preview-text {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
.preview-text.sm {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.generate-bar {
  display: flex;
  gap: 10px;
}

/* Step 2: Reply options */
.reply-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
}
.reply-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}
.reply-option {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.reply-option:hover {
  border-color: var(--border-default);
}
.reply-option.selected {
  border-color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.04);
}
.option-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.option-key {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
}
.reply-option.selected .option-key {
  background: var(--accent-blue);
  color: #fff;
}
.option-type {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 500;
}
.option-text {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-primary);
}
.option-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 8px;
  font-family: var(--font-mono);
}

.custom-reply {
  margin-bottom: 20px;
}
.custom-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
  font-weight: 500;
}
.custom-textarea {
  width: 100%;
  padding: 12px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  transition: border-color var(--transition-fast);
}
.custom-textarea:focus {
  border-color: var(--accent-blue);
}
.custom-textarea::placeholder {
  color: var(--text-tertiary);
}

.action-bar {
  display: flex;
  justify-content: space-between;
}

/* Step 3: Confirm */
.confirm-card {
  margin-bottom: 16px;
}
.confirm-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 14px;
}
.confirm-body {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
}
.confirm-text {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.confirm-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 8px;
  font-family: var(--font-mono);
}
.confirm-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.result-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px;
  text-align: center;
}
.result-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.result-ok {
  background: var(--accent-green-dim);
  color: var(--accent-green);
}
.result-fail {
  background: var(--accent-red-dim);
  color: var(--accent-red);
}
.result-text {
  font-size: 15px;
  font-weight: 600;
}
.result-detail {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 6px;
  max-width: 400px;
}

.extract-progress {
  margin-top: 16px;
  padding: 14px 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}
.progress-bar {
  height: 3px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 10px;
}
.progress-fill {
  height: 100%;
  background: var(--accent-blue);
  border-radius: 2px;
  animation: progress-indeterminate 2s ease-in-out infinite;
}
@keyframes progress-indeterminate {
  0% { width: 0%; margin-left: 0%; }
  50% { width: 40%; margin-left: 30%; }
  100% { width: 0%; margin-left: 100%; }
}
.progress-text {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
