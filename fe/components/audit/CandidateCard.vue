<script setup lang="ts">
import { friendlySourceLabel, severityFromConfidence } from '~/utils/auditHelpers'

interface CandidateResult {
  candidate_id: string
  title: string | null
  status: string
  quality_score: number
  confidence: number
  support_events: number
  novelty_status: string
  support_accounts?: number
  pattern_card: {
    formal_pattern_name?: string
    plain_language?: string
    source_types?: string[]
    support_accounts?: number
  }
}

interface Props {
  candidate: CandidateResult
  isSelected: boolean
}

interface Emits {
  (e: 'click'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const severity = computed(() => severityFromConfidence(props.candidate.confidence))

const patternName = computed(() => {
  return props.candidate.pattern_card.formal_pattern_name || props.candidate.title || 'Unnamed Pattern'
})

const briefSnippet = computed(() => {
  const text = (props.candidate.pattern_card.plain_language ?? '').trim()
  return text.length > 90 ? text.substring(0, 87) + '...' : text
})

const friendlySources = computed(() => {
  return (props.candidate.pattern_card.source_types || [])
    .map(friendlySourceLabel)
    .join(', ')
})

const supportAccounts = computed(() => {
  return props.candidate.support_accounts ?? props.candidate.pattern_card.support_accounts ?? 0
})
</script>

<template>
  <div
    @click="emit('click')"
    class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm cursor-pointer transition-all hover:shadow-md hover:border-gray-300"
    :class="{ 'ring-2 ring-primary-500 border-primary-300': isSelected }"
  >
    <div class="flex items-start justify-between gap-2">
      <h3 class="text-sm font-semibold text-gray-900 flex-1 leading-snug">
        {{ patternName }}
      </h3>
      <span
        :class="severity.class"
        class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide flex-shrink-0"
      >
        {{ severity.label }}
      </span>
    </div>

    <p v-if="briefSnippet" class="mt-1.5 text-xs text-gray-500 leading-relaxed">
      {{ briefSnippet }}
    </p>

    <div class="mt-3 flex items-center gap-3 text-xs text-gray-600">
      <span class="font-medium">{{ candidate.support_events }} events</span>
      <span class="text-gray-300">|</span>
      <span class="font-medium">{{ supportAccounts }} accounts</span>
    </div>

    <div class="mt-2.5 flex items-center gap-2 flex-wrap">
      <span
        :class="severity.badgeClass"
        class="rounded-full px-2 py-0.5 text-[10px] font-medium"
      >
        {{ Math.round(candidate.confidence * 100) }}% confidence
      </span>
      <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
        {{ Math.round(candidate.quality_score * 100) }}% quality
      </span>
      <span
        v-if="candidate.novelty_status === 'new'"
        class="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700"
      >
        New pattern
      </span>
    </div>

    <div v-if="friendlySources" class="mt-2 text-[11px] text-gray-400 truncate">
      {{ friendlySources }}
    </div>
  </div>
</template>
