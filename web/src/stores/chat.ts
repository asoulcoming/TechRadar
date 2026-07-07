import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendMessage } from '../api'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  chartData?: any
  sources?: any[]
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const sessionId = ref<string | null>(null)
  const loading = ref(false)

  async function send(msg: string) {
    messages.value.push({ role: 'user', content: msg })
    loading.value = true

    try {
      const res = await sendMessage(msg, sessionId.value || undefined)
      sessionId.value = res.session_id

      messages.value.push({
        role: 'assistant',
        content: res.reply,
        chartData: res.chart_data,
        sources: res.sources,
      })
    } catch (e: any) {
      messages.value.push({
        role: 'assistant',
        content: `抱歉，处理请求时出错：${e.message}`,
      })
    } finally {
      loading.value = false
    }
  }

  function clear() {
    messages.value = []
    sessionId.value = null
  }

  return { messages, sessionId, loading, send, clear }
})
