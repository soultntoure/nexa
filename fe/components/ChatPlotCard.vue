<script setup lang="ts">
import { Bar, Line, Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { toChartJsConfig, type ChartSpec } from '~/utils/chartTransformer'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, Filler,
)

const props = defineProps<{ chart: ChartSpec }>()

const config = computed(() => toChartJsConfig(props.chart))

const chartComponent = computed(() => {
  const map = { bar: Bar, line: Line, pie: Pie } as const
  return map[props.chart.chart_type]
})
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
    <div class="mb-3 flex items-center justify-between">
      <h4 class="text-sm font-semibold text-gray-800">{{ chart.title }}</h4>
      <span class="rounded-full bg-primary-50 px-2 py-0.5 text-[10px] font-medium text-primary-600 uppercase">
        {{ chart.chart_type }}
      </span>
    </div>
    <div style="min-height: 220px; position: relative;">
      <component
        :is="chartComponent"
        :data="config.data"
        :options="config.options"
      />
    </div>
  </div>
</template>
