<script setup lang="ts">
import { Icon } from '@iconify/vue'

interface Props {
  status: string
  runId: string | null
  candidateCount: number
  clusterCount: number
  duration: number | null
}

interface Emits {
  (e: 'trigger'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const subtitle = computed(() => {
  switch (props.status) {
    case 'idle':
      return 'Ready to scan for fraud patterns'
    case 'streaming':
      return `Analyzing ${props.clusterCount} clusters...`
    case 'completed':
      return `Found ${props.candidateCount} patterns`
    case 'error':
      return 'An error occurred'
    default:
      return ''
  }
})

const isStreaming = computed(() => props.status === 'streaming')

const formattedDuration = computed(() => {
  if (!props.duration) return null
  const minutes = Math.floor(props.duration / 60)
  const seconds = Math.floor(props.duration % 60)
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
})
</script>

<template>
  <div class="flex items-center justify-between">
    <div class="flex-1">
      <h1 class="text-2xl font-bold text-gray-900">
        Fraud Pattern Discovery
      </h1>
      <p class="mt-1 text-sm text-gray-600">
        {{ subtitle }}
      </p>
    </div>

    <div class="flex items-center gap-3">
      <button
        @click="emit('trigger')"
        :disabled="isStreaming"
        class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Icon
          :icon="isStreaming ? 'lucide:loader' : 'lucide:play'"
          :class="{ 'animate-spin': isStreaming }"
          class="h-4 w-4"
        />
        Start New Audit
      </button>

      <div
        v-if="status === 'completed' && formattedDuration"
        class="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700"
      >
        Completed in {{ formattedDuration }}
      </div>
    </div>
  </div>
</template>
