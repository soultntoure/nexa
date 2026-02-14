<script setup lang="ts">
import { VisXYContainer, VisLine, VisAxis } from '@unovis/vue'

interface TrendPoint {
  date: string
  approved: number
  escalated: number
  blocked: number
}

const props = withDefaults(defineProps<{
  data: TrendPoint[]
  height?: number
}>(), {
  height: 120,
})

const x = (_: TrendPoint, i: number) => i
const yApproved = (d: TrendPoint) => d.approved
const yEscalated = (d: TrendPoint) => d.escalated
const yBlocked = (d: TrendPoint) => d.blocked

const xTickFormat = (i: number) => {
  const point = props.data[i]
  if (!point) return ''
  const d = new Date(point.date + 'T00:00:00')
  if (props.data.length <= 7) {
    return d.toLocaleDateString('en-US', { weekday: 'short' })
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const xNumTicks = computed(() => {
  if (props.data.length <= 7) return props.data.length
  return Math.min(props.data.length, 6)
})
</script>

<template>
  <div>
    <VisXYContainer :data="data" :height="height" :padding="{ top: 8, right: 8, bottom: 0, left: 0 }">
      <VisLine :x="x" :y="yApproved" color="#22c55e" :line-width="2" :curve-type="'monotoneX'" />
      <VisLine :x="x" :y="yEscalated" color="#f59e0b" :line-width="2" :curve-type="'monotoneX'" />
      <VisLine :x="x" :y="yBlocked" color="#ef4444" :line-width="2" :curve-type="'monotoneX'" />
      <VisAxis type="x" :tick-format="xTickFormat" :num-ticks="xNumTicks" :grid-line="false" :tick-line="false" :domain-line="false" />
      <VisAxis type="y" :num-ticks="4" :grid-line="true" :tick-line="false" :domain-line="false" />
    </VisXYContainer>

    <!-- Legend -->
    <div class="mt-2 flex items-center justify-center gap-4">
      <div class="flex items-center gap-1.5">
        <span class="h-0.5 w-3 rounded bg-green-500" />
        <span class="text-[10px] text-gray-500">Approved</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="h-0.5 w-3 rounded bg-amber-500" />
        <span class="text-[10px] text-gray-500">Escalated</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="h-0.5 w-3 rounded bg-red-500" />
        <span class="text-[10px] text-gray-500">Blocked</span>
      </div>
    </div>
  </div>
</template>
