<template>
  <div class="dashboard">
    <!-- Search Bar -->
    <SearchBar @search="handleSearch" />

    <!-- Stats Overview -->
    <div class="stat-cards">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-value">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- Hot Topics + Trend Chart -->
    <div class="dashboard-grid">
      <div class="card">
        <h3>🔥 当前热门技术主题</h3>
        <HotTopicCard :topics="hotTopics" />
      </div>
      <div class="card">
        <div class="card-header">
          <h3>📈 热度趋势</h3>
          <router-link v-if="searchQuery" :to="{ path: '/chat', query: { q: searchQuery } }" class="ask-ai-link">
            🤖 问 AI
          </router-link>
        </div>
        <TrendChart v-if="trendData" :title="trendData.title" :xAxis="trendData.xAxis" :series="trendData.series" />
        <p v-else class="placeholder-text">在搜索框中输入技术主题以查看趋势</p>
      </div>
    </div>

    <!-- Recent Posts -->
    <div class="card">
      <h3>📋 最新热点内容</h3>
      <PostList :posts="recentPosts" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SearchBar from '../components/SearchBar.vue'
import HotTopicCard from '../components/HotTopicCard.vue'
import TrendChart from '../components/TrendChart.vue'
import PostList from '../components/PostList.vue'
import { getDashboard, getTrends } from '../api'

const router = useRouter()

const stats = ref([
  { label: '监测平台', value: '4' },
  { label: '今日话题', value: '0' },
  { label: '最新内容', value: '0' },
])

const hotTopics = ref<any[]>([])
const recentPosts = ref<any[]>([])
const trendData = ref<any>(null)
const searchQuery = ref('')

async function loadDashboard() {
  try {
    const data = await getDashboard()
    hotTopics.value = data.hot_topics || []
    recentPosts.value = data.recent_posts || []
    stats.value[1].value = String(data.hot_topics?.length || 0)
    stats.value[2].value = String(data.recent_posts?.length || 0)
    if (data.active_platforms) {
      stats.value[0].value = String(data.active_platforms.length)
    }
  } catch (e) {
    console.error('Failed to load dashboard:', e)
  }
}

async function handleSearch(query: string) {
  searchQuery.value = query
  try {
    const data = await getTrends(query, undefined, 30)
    if (data.data?.length) {
      trendData.value = {
        title: `"${query}" 近 ${data.days || 30} 天热度趋势`,
        xAxis: data.data.map((d: any) => d.date),
        series: [{
          name: '热度分',
          data: data.data.map((d: any) => d.score),
        }],
      }
    }
  } catch (e) {
    console.error('Failed to load trends:', e)
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 20px 0;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

h3 {
  margin-bottom: 12px;
  font-size: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.ask-ai-link {
  font-size: 13px;
  color: var(--primary);
  padding: 2px 8px;
  border: 1px solid var(--primary);
  border-radius: 4px;
  white-space: nowrap;
}

.ask-ai-link:hover {
  background: var(--primary);
  color: white;
}

.placeholder-text {
  color: var(--text-secondary);
  padding: 40px 0;
  text-align: center;
}
</style>
