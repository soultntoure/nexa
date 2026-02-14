<script setup lang="ts">
import { VisDonut, VisSingleContainer } from '@unovis/vue'

interface DataItem {
  name: string
  value: number
}

const props = withDefaults(defineProps<{
  data: DataItem[]
  colors?: string[]
  width?: number
  height?: number
  label?: string
  sublabel?: string
}>(), {
  colors: () => ['#22c55e', '#f59e0b', '#ef4444'],
  width: 160,
  height: 160,
})

const value = (d: DataItem) => d.value
const color = (_: DataItem, i: number) => props.colors[i % props.colors.length]
</script>

<template>
  <div class="relative" :style="{ width: `${width}px`, height: `${height}px` }">
    <VisSingleContainer :height="height" :width="width" :data="data">
      <VisDonut
        :value="value"
        :color="color"
        :arc-width="20"
        :pad-angle="0.02"
        :corner-radius="2"
      />
    </VisSingleContainer>
    <div v-if="label" class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
      <span class="text-2xl font-bold text-gray-900">{{ label }}</span>
      <span v-if="sublabel" class="text-xs text-gray-400">{{ sublabel }}</span>
    </div>
  </div>
</template>
