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
  <TabsRoot :model-value="selectedStatus" @update:model-value="(v) => emit('update:selectedStatus', v as TransactionStatus)">
    <TabsList class="flex items-center gap-1 bg-gray-100 p-1 rounded-lg w-fit">
      <TabsTrigger
        v-for="tab in statusTabs"
        :key="tab.key"
        :value="tab.key"
        class="px-4 py-2 text-sm font-medium rounded-md transition-all text-gray-600 hover:text-gray-800 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
      >
        {{ tab.label }}
        <span
          class="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-gray-200/70 text-gray-500 data-[state=active]:bg-gray-200 data-[state=active]:text-gray-700"
        >
          {{ statusCounts[tab.key] }}
        </span>
      </TabsTrigger>
    </TabsList>
  </TabsRoot>
</template>
