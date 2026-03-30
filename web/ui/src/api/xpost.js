import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 600000,
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

export const getStatus = () => api.get('/status')
export const getReports = () => api.get('/radar/reports')
export const getReport = (date) => api.get(`/radar/report/${date}`)
export const getScanResult = (limit = 50, offset = 0) =>
  api.get('/radar/result', { params: { limit, offset } })
export const getInterests = () => api.get('/radar/interests')
export const updateInterests = (data) => api.put('/radar/interests', data)

/** @param {import('axios').AxiosRequestConfig} [config] 可传 { signal } 用于中止请求 */
export const runScan = (config = {}) => api.post('/radar/scan', null, config)
export const runAnalyze = (days = 7, config = {}) =>
  api.post('/radar/analyze', null, { params: { days }, ...config })
export const runDaily = (config = {}) => api.post('/radar/daily', null, config)
export const cancelRadar = () => api.post('/radar/cancel')

// Weekly report APIs
export const getWeeklyReports = () => api.get('/radar/weekly-reports')
export const getWeeklyReport = (date) => api.get(`/radar/weekly-report/${date}`)
export const runWeekly = (config = {}) => api.post('/radar/weekly', null, config)

export const extractTweet = (url) => api.post('/reply/extract', { url })
export const generateReplies = (tweet_text, handle) =>
  api.post('/reply/generate', { tweet_text, handle })
export const sendReply = (url, text, publish = false) =>
  api.post('/reply/send', { url, text, publish })

export const getAccounts = () => api.get('/accounts')
export const getRadarAccounts = () => api.get('/radar/accounts')
export const addRadarAccount = (handle, note) =>
  api.post('/radar/accounts', { handle, note })
export const removeRadarAccount = (handle) =>
  api.delete(`/radar/accounts/${handle}`)
export const restoreRadarAccount = (handle) =>
  api.put(`/radar/accounts/${handle}/restore`)

export const runPipeline = (steps) => api.post('/pipeline/run', { steps })

// Followers
export const getFollowers = () => api.get('/followers')
export const fetchFollowers = (username = 'jackaiwison') =>
  api.post('/followers/fetch', null, { params: { username } })

// Scheduler
export const getSchedulerStatus = () => api.get('/scheduler/status')
export const installScheduler = (time = '09:00') => api.post('/scheduler/install', { time })
export const uninstallScheduler = () => api.post('/scheduler/uninstall')
export const runSchedulerNow = () => api.post('/scheduler/run-now')
export const getSchedulerLogs = (lines = 50) => api.get('/scheduler/logs', { params: { lines } })

// Publish Queue
export const getPublishQueue = () => api.get('/publish/queue')
export const uploadImage = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const publishPost = (data) => api.post('/publish/post', data)
export const deletePublishTask = (taskId) => api.delete(`/publish/${taskId}`)
export const cancelPublishTask = (taskId) => api.put(`/publish/${taskId}/cancel`)
export const retryPublishTask = (taskId) => api.post(`/publish/${taskId}/retry`)
