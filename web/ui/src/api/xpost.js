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

export const runScan = () => api.post('/radar/scan')
export const runAnalyze = (days = 7) => api.post('/radar/analyze', null, { params: { days } })
export const runDaily = () => api.post('/radar/daily')

export const extractTweet = (url) => api.post('/reply/extract', { url })
export const generateReplies = (tweet_text, handle) =>
  api.post('/reply/generate', { tweet_text, handle })
export const sendReply = (url, text, publish = false) =>
  api.post('/reply/send', { url, text, publish })

export const getAccounts = () => api.get('/accounts')

export const runPipeline = (steps) => api.post('/pipeline/run', { steps })
