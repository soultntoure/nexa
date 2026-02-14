<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { CandidateResult } from '~/utils/auditTypes'
import {
  severityFromConfidence,
  confidenceExplainer,
  qualityExplainer,
  friendlySourceLabel,
} from '~/utils/auditHelpers'

interface Props {
  candidate: CandidateResult
}

const props = defineProps<Props>()

const severity = computed(() => severityFromConfidence(props.candidate.confidence))

const confidencePercent = computed(() => Math.round(props.candidate.confidence * 100))
const qualityPercent = computed(() => Math.round(props.candidate.quality_score * 100))
const confidenceHint = computed(() => confidenceExplainer(props.candidate.confidence))
const qualityHint = computed(() => qualityExplainer(props.candidate.quality_score))

const confidenceBarColor = computed(() => {
  if (props.candidate.confidence >= 0.7) return 'bg-red-500'
  if (props.candidate.confidence >= 0.4) return 'bg-yellow-500'
  return 'bg-gray-400'
})

const qualityBarColor = computed(() => {
  if (props.candidate.quality_score >= 0.7) return 'bg-green-500'
  if (props.candidate.quality_score >= 0.4) return 'bg-yellow-500'
  return 'bg-gray-400'
})

const adminBrief = computed(() => (props.candidate.pattern_card.plain_language ?? '').trim())
const analystNotes = computed(() => (props.candidate.pattern_card.analyst_notes ?? '').trim())
const supportAccounts = computed(() =>
  props.candidate.support_accounts ?? props.candidate.pattern_card.support_accounts ?? 0
)

const friendlySources = computed(() =>
  (props.candidate.pattern_card.source_types || []).map(friendlySourceLabel)
)

const showNotes = ref(false)
</script>

<template>
  <div class="space-y-5">
    <!-- Header: pattern name + severity -->
    <div class="flex items-center gap-3">
      <span
        :class="severity.class"
        class="rounded-full px-2.5 py-1 text-xs font-bold uppercase tracking-wide"
      >
        {{ severity.label }}
      </span>
      <h3 class="text-lg font-semibold text-gray-900">
        {{ candidate.pattern_card.formal_pattern_name ?? 'Untitled Pattern' }}
      </h3>
    </div>

    <!-- Score bars with explanations -->
    <div class="space-y-3">
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-gray-700">Confidence</span>
          <span class="text-sm font-semibold text-gray-900">{{ confidencePercent }}%</span>
        </div>
        <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full transition-all" :class="confidenceBarColor" :style="{ width: `${confidencePercent}%` }" />
        </div>
        <p class="mt-1 text-xs text-gray-500">{{ confidenceHint }}</p>
      </div>

      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-gray-700">Evidence Quality</span>
          <span class="text-sm font-semibold text-gray-900">{{ qualityPercent }}%</span>
        </div>
        <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full transition-all" :class="qualityBarColor" :style="{ width: `${qualityPercent}%` }" />
        </div>
        <p class="mt-1 text-xs text-gray-500">{{ qualityHint }}</p>
      </div>
    </div>

    <!-- Admin Brief -->
    <div v-if="adminBrief" class="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1.5">What was found</p>
      <p class="text-sm leading-relaxed text-gray-700">{{ adminBrief }}</p>
    </div>

    <!-- Metadata row -->
    <div class="flex flex-wrap gap-3 items-center">
      <div class="flex items-center gap-1.5 text-sm text-gray-600">
        <Icon icon="lucide:activity" class="h-4 w-4 text-gray-400" />
        <span><strong>{{ candidate.support_events }}</strong> events across <strong>{{ supportAccounts }}</strong> accounts</span>
      </div>

      <span
        v-if="candidate.novelty_status === 'new'"
        class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
      >
        New pattern
      </span>
      <span
        v-else-if="candidate.novelty_status === 'known'"
        class="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"
      >
        Known pattern
      </span>
    </div>

    <!-- Friendly sources -->
    <div v-if="friendlySources.length" class="flex flex-wrap gap-1.5">
      <span
        v-for="src in friendlySources"
        :key="src"
        class="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700"
      >
        {{ src }}
      </span>
    </div>

    <!-- Collapsible analyst notes -->
    <div v-if="analystNotes">
      <button
        @click="showNotes = !showNotes"
        class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <Icon :icon="showNotes ? 'lucide:chevron-down' : 'lucide:chevron-right'" class="h-4 w-4" />
        <Icon icon="lucide:brain" class="h-4 w-4" />
        <span>Analyst Notes</span>
      </button>
      <div v-if="showNotes" class="mt-2 rounded-lg border border-gray-200 bg-white p-3">
        <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ analystNotes }}</p>
      </div>
    </div>
  </div>
</template>
