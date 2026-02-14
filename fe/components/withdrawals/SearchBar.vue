<script setup lang="ts">
import { Icon } from '@iconify/vue'

const searchQuery = defineModel<string>('searchQuery', { default: '' })
const dateFrom = defineModel<string>('dateFrom', { default: '' })
const dateTo = defineModel<string>('dateTo', { default: '' })

const emit = defineEmits<{
  search: []
}>()
</script>

<template>
  <div class="flex flex-wrap items-center gap-4">
    <div class="relative flex-1 min-w-[280px] max-w-md">
      <Icon icon="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by name, email, or transaction ID..."
        class="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        @input="emit('search')"
      >
    </div>
    <div class="flex items-center gap-2">
      <input
        v-model="dateFrom"
        type="date"
        class="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
      >
      <span class="text-gray-400 text-sm">to</span>
      <input
        v-model="dateTo"
        type="date"
        class="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
      >
    </div>
  </div>
</template>
