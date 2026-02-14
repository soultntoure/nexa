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
    <PaginationRoot
      :total="totalPages"
      :items-per-page="1"
      :page="currentPage"
      @update:page="emit('update:currentPage', $event)"
    >
      <PaginationList v-slot="{ items }" class="flex items-center gap-1">
        <PaginationPrev class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          Previous
        </PaginationPrev>
        <template v-for="(page, index) in items" :key="index">
          <PaginationListItem
            v-if="page.type === 'page'"
            :value="page.value"
            class="h-8 w-8 rounded-lg text-sm font-medium text-gray-600 bg-white border border-gray-300 hover:bg-gray-50 transition-colors data-[selected]:bg-primary-600 data-[selected]:text-white data-[selected]:border-primary-600"
          >
            {{ page.value }}
          </PaginationListItem>
          <PaginationEllipsis v-else :index="index" class="flex h-8 w-8 items-center justify-center text-gray-500">
            ...
          </PaginationEllipsis>
        </template>
        <PaginationNext class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          Next
        </PaginationNext>
      </PaginationList>
    </PaginationRoot>
  </div>
</template>
