<template>
  <div class="trend-chart-wrapper">
    <h4 v-if="title" class="chart-title">{{ title }}</h4>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  title?: string
  xAxis: string[]
  series: { name: string; data: number[] }[]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chartRef.value || !props.series.length) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  chart.setOption({
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: props.series.map(s => s.name),
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: props.xAxis,
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { fontSize: 11, formatter: '{value}' },
    },
    series: props.series.map(s => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
    })),
    color: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'],
  }, true)
}

onMounted(() => {
  nextTick(renderChart)
})

watch(() => [props.xAxis, props.series], () => {
  nextTick(renderChart)
}, { deep: true })
</script>

<style scoped>
.trend-chart-wrapper {
  width: 100%;
}

.chart-title {
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.chart-container {
  width: 100%;
  height: 300px;
}
</style>
