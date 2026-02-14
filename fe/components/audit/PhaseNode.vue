<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Phase } from '~/utils/auditTypes'

interface Props {
  phase: Phase
}

const props = defineProps<Props>()

const phaseLabels: Record<string, { active: string; completed: string }> = {
  extract: {
    active: 'Scanning recent transactions for suspicious activity...',
    completed: 'Evidence collected'
  },
  embed_cluster: {
    active: 'Grouping similar suspicious patterns together...',
    completed: 'Patterns grouped'
  },
  investigate: {
    active: 'AI agent deep-diving into each pattern...',
    completed: 'Analysis complete'
  },
  artifacts: {
    active: 'Compiling the findings report...',
    completed: 'Report ready'
  }
}

const displayLabel = computed(() => {
  const labels = phaseLabels[props.phase.name]
  if (!labels) return props.phase.label

  if (props.phase.status === 'active') return labels.active
  if (props.phase.status === 'completed') {
    return props.phase.detail || labels.completed
  }
  return props.phase.label
})

const iconConfig = computed(() => {
  switch (props.phase.status) {
    case 'pending':
      return { icon: 'lucide:circle', class: 'text-gray-400' }
    case 'active':
      return { icon: 'lucide:loader', class: 'text-primary-500 animate-spin' }
    case 'completed':
      return { icon: 'lucide:check-circle', class: 'text-green-500' }
    default:
      return { icon: 'lucide:circle', class: 'text-gray-400' }
  }
})

const textClass = computed(() => {
  switch (props.phase.status) {
    case 'pending':
      return 'text-gray-400'
    case 'active':
      return 'text-gray-900 font-semibold'
    case 'completed':
      return 'text-gray-700'
    default:
      return 'text-gray-600'
  }
})

const formattedDuration = computed(() => {
  if (!props.phase.duration) return null
  return `${props.phase.duration.toFixed(1)}s`
})
</script>

<template>
  <div class="flex items-start gap-3 py-2">
    <Icon
      :icon="iconConfig.icon"
      :class="iconConfig.class"
      class="h-5 w-5 flex-shrink-0"
    />

    <div class="flex-1 space-y-1">
      <div :class="textClass" class="text-sm font-medium">
        {{ displayLabel }}
      </div>

      <div
        v-if="phase.detail && phase.status !== 'completed'"
        class="text-xs text-gray-500"
      >
        {{ phase.detail }}
      </div>

      <div
        v-if="formattedDuration && phase.status === 'completed'"
        class="text-xs text-gray-500"
      >
        Duration: {{ formattedDuration }}
      </div>
    </div>
  </div>
</template>
