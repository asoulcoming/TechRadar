<template>
  <div class="hot-topic-list">
    <div v-if="topics.length === 0" class="placeholder-text">加载中...</div>
    <div v-for="(t, i) in topics" :key="t.topic" class="topic-item">
      <span class="topic-rank">{{ i + 1 }}</span>
      <span class="topic-name">{{ t.topic }}</span>
      <span class="topic-score">{{ t.score || t.avg_score }}分</span>
      <span v-if="t.change_percent" :class="['topic-change', t.trend === '上升' ? 'up' : 'down']">
        {{ t.change_percent > 0 ? '↑' : '↓' }}{{ Math.abs(t.change_percent) }}%
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ topics: any[] }>()
</script>

<style scoped>
.topic-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.topic-item:last-child {
  border-bottom: none;
}

.topic-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.topic-item:nth-child(1) .topic-rank { background: #fbbf24; color: white; }
.topic-item:nth-child(2) .topic-rank { background: #94a3b8; color: white; }
.topic-item:nth-child(3) .topic-rank { background: #d97706; color: white; }

.topic-name {
  flex: 1;
  font-weight: 500;
}

.topic-score {
  font-weight: 600;
  color: var(--primary);
}

.topic-change {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.topic-change.up { color: var(--success); background: #dcfce7; }
.topic-change.down { color: var(--danger); background: #fee2e2; }

.placeholder-text {
  color: var(--text-secondary);
  padding: 20px;
  text-align: center;
}
</style>
