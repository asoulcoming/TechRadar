<template>
  <div class="search-bar">
    <div class="search-input-wrapper">
      <span class="search-icon">🔍</span>
      <input
        v-model="query"
        type="text"
        placeholder="输入技术主题或问题，如：GEO 最近热度、对比 Python 和 Go..."
        @keyup.enter="$emit('search', query)"
      />
    </div>
    <button class="btn btn-primary" @click="$emit('search', query)" :disabled="!query.trim()">
      查询
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineEmits<{ search: [query: string] }>()

const query = ref('')
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input-wrapper {
  flex: 1;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
}

.search-input-wrapper input {
  padding-left: 36px;
  font-size: 15px;
}

.search-bar button {
  padding: 10px 24px;
  font-size: 15px;
}
</style>
