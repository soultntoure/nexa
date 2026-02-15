<script setup lang="ts">
import { Bar, Line } from 'vue-chartjs'
import {
  BarElement, CategoryScale, Chart as ChartJS,
  Legend, LineElement, LinearScale,
  PointElement, Title, Tooltip,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend)

interface DriftChartData {
  labels: string[]
  multipliers: number[]
  trends: number[]
}

const props = defineProps<{ chartData: DriftChartData }>()

const barData = computed(() => ({
  labels: props.chartData.labels,
  datasets: [{
    label: 'Average Weight',
    data: props.chartData.multipliers,
    backgroundColor: props.chartData.multipliers.map(v =>
      v > 2.0 ? '#ef4444' : v < 0.5 ? '#f59e0b' : '#3b82f6',
    ),
  }],
}))

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    title: { display: true, text: 'Average Signal Weight', font: { size: 13 } },
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const v = ctx.raw as number
          if (v > 2.0) return `${v.toFixed(2)} (unusually high)`
          if (v < 0.5) return `${v.toFixed(2)} (unusually low)`
          return `${v.toFixed(2)} (normal range)`
        },
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      title: { display: true, text: 'Weight', font: { size: 11 } },
    },
  },
}

const trendLabels: Record<number, string> = { 1: 'Increasing', 0: 'Stable', '-1': 'Decreasing' }

const lineData = computed(() => ({
  labels: props.chartData.labels,
  datasets: [{
    label: 'Direction',
    data: props.chartData.trends,
    borderColor: '#8b5cf6',
    backgroundColor: '#8b5cf680',
    borderWidth: 2,
    fill: false,
    tension: 0.3,
  }],
}))

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    title: { display: true, text: 'Signal Weight Trend', font: { size: 13 } },
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => trendLabels[ctx.raw as number] ?? 'Stable',
      },
    },
  },
  scales: {
    y: {
      min: -1.5,
      max: 1.5,
      ticks: {
        stepSize: 1,
        callback: (v: number) => trendLabels[v] ?? '',
      },
      title: { display: true, text: 'Direction', font: { size: 11 } },
    },
  },
}
</script>

<template>
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
    <div class="h-[220px]">
      <Bar :data="barData" :options="barOptions" />
    </div>
    <div class="h-[220px]">
      <Line :data="lineData" :options="lineOptions" />
    </div>
  </div>
</template>
