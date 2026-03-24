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

export const runPipeline = (steps) => api.post('/pipeline/run', { steps })
