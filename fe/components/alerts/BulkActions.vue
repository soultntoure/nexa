<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  selectedCount: number
  loading: boolean
}>()

const emit = defineEmits<{
  action: [action: string]
}>()
</script>

<template>
  <div v-if="selectedCount > 0" class="mb-4 flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
    <span class="text-sm font-medium text-gray-700">{{ selectedCount }} selected</span>
    <div class="flex gap-2">
      <button
        class="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
        :disabled="loading"
        @click="emit('action', 'lock_accounts')"
      >
        <Icon icon="lucide:lock" class="mr-1 inline h-3.5 w-3.5" />
        Lock Accounts
      </button>
      <button
        class="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
        :disabled="loading"
        @click="emit('action', 'freeze_withdrawals')"
      >
        <Icon icon="lucide:snowflake" class="mr-1 inline h-3.5 w-3.5" />
        Freeze Withdrawals
      </button>
      <button
        class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        @click="emit('action', 'export')"
      >
        <Icon icon="lucide:download" class="mr-1 inline h-3.5 w-3.5" />
        Export
      </button>
    </div>
  </div>
</template>
