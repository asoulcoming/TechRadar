<template>
  <div class="chat-view">
    <div class="chat-header">
      <button class="btn btn-secondary" @click="chatStore.clear()">新对话</button>
    </div>

    <!-- Messages -->
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="chatStore.messages.length === 0" class="chat-welcome">
        <h2>👋 你好！我是 AI 热点洞察助手</h2>
        <p>试试问我：</p>
        <div class="example-queries">
          <button
            v-for="q in exampleQueries"
            :key="q"
            class="btn btn-secondary"
            @click="chatStore.send(q)"
          >{{ q }}</button>
        </div>
      </div>

      <div v-for="(msg, i) in chatStore.messages" :key="i"
           :class="['message', msg.role]">
        <div class="message-avatar">{{ msg.role === 'user' ? '🙋' : '🤖' }}</div>
        <div class="message-content">
          <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          <TrendChart
            v-if="msg.chartData"
            :title="msg.chartData.title"
            :xAxis="msg.chartData.xAxis"
            :series="msg.chartData.series"
            class="message-chart"
          />
          <div v-if="msg.sources?.length" class="message-sources">
            <strong>📎 来源：</strong>
            <a v-for="(s, j) in msg.sources" :key="j" :href="s.url" target="_blank" class="source-link">
              [{{ s.platform }}] {{ s.title }}
            </a>
          </div>
        </div>
      </div>

      <div v-if="chatStore.loading" class="message assistant">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="typing-indicator">思考中...</div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="chat-input">
      <input
        v-model="input"
        type="text"
        placeholder="输入技术话题，如：最近一周 Rust 在 GitHub 上热度如何？"
        @keyup.enter="sendMessage"
        :disabled="chatStore.loading"
      />
      <button class="btn btn-primary" @click="sendMessage" :disabled="chatStore.loading || !input.trim()">
        发送
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '../stores/chat'
import TrendChart from '../components/TrendChart.vue'

const route = useRoute()
const chatStore = useChatStore()
const input = ref('')
const messagesContainer = ref<HTMLElement>()

const exampleQueries = [
  '今天 GitHub 上最热的 Go 项目是什么？',
  '最近一周 AI 大模型在知乎上的热度趋势',
  '对比 Python 和 Rust 的热度',
  'B站 最近有哪些热门的编程教学视频？',
]

function renderMarkdown(text: string): string {
  // Simple markdown rendering for chat
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/## (.+)/g, '<h4>$1</h4>')
    .replace(/### (.+)/g, '<h5>$1</h5>')
}

async function sendMessage() {
  const msg = input.value.trim()
  if (!msg || chatStore.loading) return
  input.value = ''
  await chatStore.send(msg)
  await nextTick()
  // Scroll to bottom
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onMounted(async () => {
  const query = route.query.q as string
  if (query) {
    await chatStore.send(query)
  }
})
</script>

<style scoped>
.chat-view {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
}

.chat-header {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.chat-welcome {
  text-align: center;
  padding: 60px 20px;
}

.chat-welcome h2 {
  margin-bottom: 12px;
}

.chat-welcome p {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.example-queries {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 24px;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-content {
  max-width: 80%;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 14px;
  line-height: 1.7;
  font-size: 14px;
}

.message.user .message-text {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.message-chart {
  margin-top: 10px;
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 8px;
}

.message-sources {
  margin-top: 8px;
  font-size: 13px;
}

.source-link {
  display: inline-block;
  margin-right: 8px;
  font-size: 12px;
}

.typing-indicator {
  color: var(--text-secondary);
  font-style: italic;
  padding: 10px 14px;
  font-size: 14px;
}

.chat-input {
  display: flex;
  gap: 8px;
  padding: 16px 0;
  border-top: 1px solid var(--border);
}

.chat-input input {
  flex: 1;
}

.chat-input button {
  padding: 8px 20px;
}
</style>
