<template>
  <div id="app-layout">
    <header class="app-header">
      <div class="container header-content">
        <router-link to="/" class="logo">🔥 AI 热点洞察</router-link>
        <nav>
          <router-link to="/">仪表盘</router-link>
          <router-link to="/chat">对话</router-link>
          <router-link to="/reports">日报</router-link>
        </nav>
      </div>
    </header>
    <main class="container main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.app-header {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  padding: 12px 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: var(--text) !important;
}

nav {
  display: flex;
  gap: 24px;
}

nav a {
  color: var(--text-secondary);
  font-size: 15px;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

nav a:hover, nav a.router-link-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.main-content {
  padding-top: 24px;
  padding-bottom: 48px;
}
</style>
