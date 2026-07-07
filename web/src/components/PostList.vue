<template>
  <div class="post-list">
    <div v-if="posts.length === 0" class="placeholder-text">暂无内容</div>
    <a v-for="p in posts" :key="p.url || p.title" :href="p.url" target="_blank" class="post-item">
      <span class="post-platform">
        {{ platformIcon(p.platform) }} {{ platformName(p.platform) }}
      </span>
      <span class="post-title">{{ p.title }}</span>
      <span class="post-author">by {{ p.author }}</span>
      <span class="post-engagement" v-if="p.likes">
        👍 {{ p.likes }} 💬 {{ p.comments }}
      </span>
    </a>
  </div>
</template>

<script setup lang="ts">
defineProps<{ posts: any[] }>()

function platformIcon(plat: string): string {
  const icons: Record<string, string> = {
    bilibili: '📺', github: '🐙', xiaohongshu: '📕', zhihu: '💡',
  }
  return icons[plat] || '📌'
}

function platformName(plat: string): string {
  const names: Record<string, string> = {
    bilibili: 'B站', github: 'GitHub', xiaohongshu: '小红书', zhihu: '知乎',
  }
  return names[plat] || plat
}
</script>

<style scoped>
.post-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  transition: background 0.15s;
}

.post-item:hover {
  background: #f1f5f9;
}

.post-item:last-child {
  border-bottom: none;
}

.post-platform {
  font-size: 12px;
  white-space: nowrap;
  min-width: 80px;
}

.post-title {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.post-author {
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.post-engagement {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.placeholder-text {
  color: var(--text-secondary);
  padding: 20px;
  text-align: center;
}
</style>
