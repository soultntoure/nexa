<script setup lang="ts">
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ select: [query: string] }>()

const examples = [
  'Show me accounts that deposited but traded minimally',
  'Which customers have multiple payment methods from different countries?',
  'Find velocity abuse patterns in the last 7 days',
  "What's our auto-approval rate this week?",
]
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center">
    <div class="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50">
      <Icon icon="lucide:message-square" class="h-8 w-8 text-primary-500" />
    </div>
    <h2 class="text-lg font-semibold text-gray-800">Ask anything about your data</h2>
    <p class="mt-1 text-sm text-gray-500">Use natural language to query transactions, detect fraud, and analyze patterns</p>

    <div class="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
      <button
        v-for="example in examples"
        :key="example"
        class="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-left text-sm text-gray-600 transition-all hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
        @click="emit('select', example)"
      >
        <Icon icon="lucide:sparkles" class="mb-1 h-4 w-4 text-primary-400" />
        <span class="block">{{ example }}</span>
      </button>
    </div>
  </div>
</template>
