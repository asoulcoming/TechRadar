import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Chat
export async function sendMessage(message: string, sessionId?: string) {
  const { data } = await api.post('/chat', { message, session_id: sessionId })
  return data
}

// Dashboard
export async function getDashboard() {
  const { data } = await api.get('/dashboard')
  return data
}

// Trends
export async function getTrends(topic: string, platform?: string, days = 30) {
  const { data } = await api.get('/trends', { params: { topic, platform, days } })
  return data
}

// Hot Topics
export async function getHotTopics(platform?: string, limit = 20) {
  const { data } = await api.get('/topics/hot', { params: { platform, limit } })
  return data
}

// Reports
export async function getLatestReport() {
  const { data } = await api.get('/reports/latest')
  return data
}

export async function getReports(from?: string, to?: string) {
  const { data } = await api.get('/reports', { params: { from, to } })
  return data
}

export async function triggerReport(date?: string) {
  const { data } = await api.post('/reports/generate', null, { params: { target_date: date } })
  return data
}

// Monitoring Topics
export async function getMonitoredTopics() {
  const { data } = await api.get('/topics/monitor')
  return data
}

export async function addMonitoredTopic(topic: string, keywords: string, platforms: string) {
  const { data } = await api.post('/topics/monitor', { topic, keywords, platforms })
  return data
}
