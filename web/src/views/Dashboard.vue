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
        <h3>📈 热度趋势</h3>
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

async function loadDashboard() {
  try {
    const data = await getDashboard()
    hotTopics.value = data.hot_topics || []
    recentPosts.value = data.recent_posts || []
    stats.value[2].value = String(data.recent_posts?.length || 0)
  } catch (e) {
    console.error('Failed to load dashboard:', e)
  }
}

async function handleSearch(query: string) {
  // Navigate to chat view with query
  router.push({ path: '/chat', query: { q: query } })
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

.placeholder-text {
  color: var(--text-secondary);
  padding: 40px 0;
  text-align: center;
}
</style>
