<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { computed, ref } from 'vue'
interface SqlFinding {
  query?: string
  result?: string
  insight?: string
  query_summary?: string
  result_summary?: string
}

interface Props {
  findings: SqlFinding[]
}

const props = defineProps<Props>()

const expandedIndex = ref<number | null>(null)

const normalizedFindings = computed(() => {
  const seen = new Set<string>()
  return props.findings
    .map((finding) => {
      const query = String(finding.query ?? finding.query_summary ?? '').trim()
      const result = String(finding.result ?? finding.result_summary ?? '').trim()
      const rawInsight = String(finding.insight ?? finding.result_summary ?? '').trim()
      const insight = normalizeInsight(rawInsight, result, query)
      return { query, result, insight }
    })
    .filter(finding => finding.query.length > 0 || finding.result.length > 0 || finding.insight.length > 0)
    .filter((finding) => {
      const key = `${finding.query}|${finding.result}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
})

function toggleExpand(index: number): void {
  expandedIndex.value = expandedIndex.value === index ? null : index
}

function normalizeInsight(rawInsight: string, result: string, query: string): string {
  const looksLikeSerializedQuery = rawInsight.startsWith('{') && rawInsight.includes('query')
  if (rawInsight && !looksLikeSerializedQuery) return rawInsight
  if (result) return result
  if (query) return 'SQL correlation extracted from transaction data.'
  return ''
}
</script>

<template>
  <div class="space-y-4">
    <div v-if="normalizedFindings.length === 0" class="text-center py-8">
      <Icon icon="lucide:database-zap" class="mx-auto h-12 w-12 text-gray-300 mb-3" />
      <p class="text-sm text-gray-500">No SQL findings</p>
    </div>

    <div v-for="(finding, idx) in normalizedFindings" :key="idx" class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Finding {{ idx + 1 }}</p>
      <div class="flex items-start gap-2 mb-3">
        <Icon icon="lucide:lightbulb" class="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <p class="text-sm text-gray-900 font-medium leading-relaxed">{{ finding.insight }}</p>
      </div>

      <button
        type="button"
        class="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors"
        @click="toggleExpand(idx)"
      >
        <Icon :icon="expandedIndex === idx ? 'lucide:chevron-down' : 'lucide:chevron-right'" class="h-4 w-4" />
        <span>{{ expandedIndex === idx ? 'Hide' : 'Show' }} SQL query</span>
      </button>

      <div v-if="expandedIndex === idx" class="mt-3 rounded-lg border border-gray-200 bg-gray-900 text-gray-100 overflow-hidden">
        <div class="bg-gray-800 px-3 py-1.5 flex items-center justify-between">
          <span class="text-xs font-medium text-gray-300">SQL</span>
        </div>
        <pre class="p-3 overflow-x-auto text-xs font-mono">{{ finding.query }}</pre>
        <div class="border-t border-gray-700 px-3 py-2 bg-gray-800">
          <span class="text-xs text-gray-400">Result: {{ finding.result }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
