<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  hasTableData: boolean
  hasMessages: boolean
  showHistory: boolean
}>()

const emit = defineEmits<{
  toggleHistory: []
  exportResults: []
  clearChat: []
}>()
</script>

<template>
  <div class="mb-4 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Natural Language Query</h1>
      <p class="mt-1 text-sm text-gray-500">Ask questions about your payment data using AI</p>
    </div>
    <div class="flex items-center gap-2">
      <button
        class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
        @click="emit('toggleHistory')"
      >
        <Icon icon="lucide:history" class="h-4 w-4" />
        History
      </button>
      <button
        v-if="hasTableData"
        class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
        @click="emit('exportResults')"
      >
        <Icon icon="lucide:download" class="h-4 w-4" />
        Export
      </button>
      <button
        v-if="hasMessages"
        class="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
        @click="emit('clearChat')"
      >
        <Icon icon="lucide:trash-2" class="h-4 w-4" />
        Clear
      </button>
    </div>
  </div>
</template>
