<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { computed } from 'vue'
interface WebReference {
  title?: string
  url?: string
  snippet?: string
  relevance?: string
}

interface Props {
  references: WebReference[]
}

const props = defineProps<Props>()

const normalizedReferences = computed(() => {
  return props.references
    .map((ref) => ({
      title: String(ref.title ?? '').trim(),
      url: String(ref.url ?? '').trim(),
      snippet: String(ref.snippet ?? ref.relevance ?? '').trim(),
    }))
    .filter(ref => ref.title.length > 0 || ref.url.length > 0 || ref.snippet.length > 0)
})
</script>

<template>
  <div class="space-y-3">
    <div v-if="normalizedReferences.length === 0" class="text-center py-8">
      <Icon icon="lucide:globe-lock" class="mx-auto h-12 w-12 text-gray-300 mb-3" />
      <p class="text-sm text-gray-500">No web references found</p>
    </div>

    <div
      v-for="(ref, idx) in normalizedReferences"
      :key="idx"
      class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div class="flex items-start gap-2 mb-2">
        <Icon icon="lucide:link" class="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
        <h4 class="text-sm font-semibold text-gray-900 leading-tight">{{ ref.title || ref.url || 'External reference' }}</h4>
      </div>

      <p v-if="ref.snippet" class="text-sm text-gray-600 leading-relaxed mb-3">{{ ref.snippet }}</p>

      <a
        v-if="ref.url"
        :href="ref.url"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
      >
        <span>Open Link</span>
        <Icon icon="lucide:external-link" class="h-4 w-4" />
      </a>
    </div>
  </div>
</template>
