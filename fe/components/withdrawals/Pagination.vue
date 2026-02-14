<script setup lang="ts">
defineProps<{
  currentPage: number
  totalPages: number
  shownCount: number
  totalCount: number
}>()

const emit = defineEmits<{
  'update:currentPage': [value: number]
}>()
</script>

<template>
  <div class="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
    <p class="text-sm text-gray-600">
      Showing {{ shownCount }} of {{ totalCount }} withdrawals
    </p>
    <div class="flex items-center gap-2">
      <button
        class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="currentPage <= 1"
        @click="emit('update:currentPage', currentPage - 1)"
      >
        Previous
      </button>
      <span class="text-sm text-gray-600 px-2">
        Page {{ currentPage }} of {{ totalPages || 1 }}
      </span>
      <button
        class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="currentPage >= totalPages"
        @click="emit('update:currentPage', currentPage + 1)"
      >
        Next
      </button>
    </div>
  </div>
</template>
