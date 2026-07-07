<template>
  <div class="reports-view">
    <div class="reports-header">
      <h2>📋 技术热点日报</h2>
      <button class="btn btn-primary" @click="generateReport" :disabled="generating">
        {{ generating ? '生成中...' : '生成最新日报' }}
      </button>
    </div>

    <div v-if="reports.length === 0" class="placeholder-text">
      暂无日报，点击"生成最新日报"按钮创建第一份日报。
    </div>

    <div v-for="report in reports" :key="report.id" class="card report-card">
      <div class="report-meta">
        <h3>{{ report.title }}</h3>
        <span class="report-date">{{ report.report_date }}</span>
      </div>
      <div class="report-summary" v-html="renderMarkdown(report.summary)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getReports, triggerReport } from '../api'

const reports = ref<any[]>([])
const generating = ref(false)

function renderMarkdown(text: string): string {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/## (.+)/g, '<h4>$1</h4>')
    .replace(/### (.+)/g, '<h5>$1</h5>')
}

async function loadReports() {
  try {
    const data = await getReports()
    reports.value = data.reports || []
  } catch (e) {
    console.error('Failed to load reports:', e)
  }
}

async function generateReport() {
  generating.value = true
  try {
    await triggerReport()
    await loadReports()
  } catch (e) {
    console.error('Failed to generate report:', e)
  } finally {
    generating.value = false
  }
}

onMounted(loadReports)
</script>

<style scoped>
.reports-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.report-card {
  margin-bottom: 20px;
}

.report-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.report-date {
  color: var(--text-secondary);
  font-size: 14px;
}

.report-summary {
  font-size: 14px;
  line-height: 1.8;
}

.report-summary :deep(h4) {
  margin: 16px 0 8px;
  font-size: 15px;
}

.report-summary :deep(h5) {
  margin: 12px 0 6px;
  font-size: 14px;
}

.placeholder-text {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 20px;
}
</style>
