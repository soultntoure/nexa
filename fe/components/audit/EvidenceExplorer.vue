<script setup lang="ts">
import { Icon } from '@iconify/vue'
interface EvidenceUnit {
  source?: string
  source_name?: string
  source_type?: string
  text?: string
  confidence?: number
  score?: number
  withdrawal_id?: string
  type?: string
  summary?: string
  result?: string
  query?: string
  snippet?: string
  evidence_type?: string
  rank?: number
  unit_id?: string
}

interface Props {
  evidence: EvidenceUnit[]
}

const props = defineProps<Props>()

const normalizedEvidence = computed(() => {
  return props.evidence
    .map((unit) => {
      const rank = Number(unit.rank)
      const fallbackConfidence = Number.isFinite(rank)
        ? Math.max(0.2, 1 - (Math.max(rank, 1) - 1) * 0.15)
        : 0.5

      return {
        source: String(unit.source_name ?? unit.source_type ?? unit.source ?? unit.type ?? unit.evidence_type ?? 'evidence'),
        text: String(unit.text ?? unit.snippet ?? unit.summary ?? unit.result ?? unit.query ?? '').trim(),
        confidence: Number(unit.confidence ?? fallbackConfidence),
        score: Number(unit.score ?? 0),
        rank: Number.isFinite(rank) ? rank : 999,
        withdrawal_id: String(unit.withdrawal_id ?? unit.unit_id ?? ''),
      }
    })
    .filter(unit => unit.text.length > 0)
})

const sortedEvidence = computed(() => {
  return [...normalizedEvidence.value].sort((a, b) => {
    if (b.confidence !== a.confidence) return b.confidence - a.confidence
    return a.rank - b.rank
  })
})

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'text-green-500'
  if (confidence >= 0.4) return 'text-yellow-500'
  return 'text-red-500'
}

function getSourceBadgeClass(source: string): string {
  const sourceLower = source.toLowerCase()
  if (sourceLower.includes('identity')) return 'bg-blue-100 text-blue-700'
  if (sourceLower.includes('financial')) return 'bg-green-100 text-green-700'
  if (sourceLower.includes('cross')) return 'bg-purple-100 text-purple-700'
  if (sourceLower.includes('web')) return 'bg-orange-100 text-orange-700'
  return 'bg-gray-100 text-gray-700'
}

function formatSource(source: string): string {
  return source
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .map(token => token ? token.charAt(0).toUpperCase() + token.slice(1) : token)
    .join(' ')
}
</script>

<template>
  <div class="space-y-3">
    <div v-if="sortedEvidence.length === 0" class="text-center py-8">
      <Icon icon="lucide:file-x" class="mx-auto h-12 w-12 text-gray-300 mb-3" />
      <p class="text-sm text-gray-500">No evidence units found</p>
    </div>

    <div
      v-for="(unit, idx) in sortedEvidence"
      :key="idx"
      class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-medium px-2 py-1 rounded-full" :class="getSourceBadgeClass(unit.source)">
          {{ formatSource(unit.source) }}
        </span>
        <div class="flex items-center gap-1.5 text-sm">
          <span class="text-gray-600">Confidence:</span>
          <Icon icon="lucide:circle" class="h-3 w-3" :class="getConfidenceColor(unit.confidence)" />
          <span class="font-medium text-gray-900">{{ Math.round(unit.confidence * 100) }}%</span>
        </div>
      </div>

      <p class="text-sm text-gray-700 leading-relaxed">{{ unit.text }}</p>

      <div v-if="unit.withdrawal_id" class="mt-2 pt-2 border-t border-gray-100">
        <span class="text-xs text-gray-500">Ref: {{ unit.withdrawal_id }}</span>
      </div>
    </div>
  </div>
</template>
