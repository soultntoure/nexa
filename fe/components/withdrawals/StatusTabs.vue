<script setup lang="ts">
import type { TransactionStatus } from '~/composables/useTransactions'

defineProps<{
  selectedStatus: TransactionStatus
  statusCounts: Record<TransactionStatus, number>
}>()

const emit = defineEmits<{
  'update:selectedStatus': [value: TransactionStatus]
}>()

const statusTabs: { key: TransactionStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'blocked', label: 'Blocked' },
]
</script>

<template>
  <div class="flex items-center gap-1 bg-gray-100 p-1 rounded-lg w-fit">
    <button
      v-for="tab in statusTabs"
      :key="tab.key"
      class="px-4 py-2 text-sm font-medium rounded-md transition-all"
      :class="selectedStatus === tab.key
        ? 'bg-white text-gray-900 shadow-sm'
        : 'text-gray-600 hover:text-gray-800'"
      @click="emit('update:selectedStatus', tab.key)"
    >
      {{ tab.label }}
      <span
        class="ml-1.5 px-1.5 py-0.5 text-xs rounded-full"
        :class="selectedStatus === tab.key ? 'bg-gray-200 text-gray-700' : 'bg-gray-200/70 text-gray-500'"
      >
        {{ statusCounts[tab.key] }}
      </span>
    </button>
  </div>
</template>
