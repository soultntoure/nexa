<script setup lang="ts">
interface CandidateResult {
  candidate_id: string
  title: string | null
  status: string
  quality_score: number
  confidence: number
  support_events: number
  novelty_status: string
  pattern_card: {
    formal_pattern_name?: string
    plain_language?: string
    source_types?: string[]
    support_accounts?: number
  }
}

interface Props {
  candidates: CandidateResult[]
}

interface Emits {
  (e: 'select-candidate', candidateId: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const selectedId = ref<string | null>(null)

const sortedCandidates = computed(() => {
  return [...props.candidates].sort((a, b) => b.quality_score - a.quality_score)
})

function handleSelect(candidateId: string): void {
  selectedId.value = candidateId
  emit('select-candidate', candidateId)
}
</script>

<template>
  <div class="mt-4">
    <div class="mb-3 flex items-center gap-2">
      <h2 class="text-lg font-semibold text-gray-900">
        Discovered Patterns
      </h2>
      <span class="rounded-full bg-primary-100 px-2.5 py-0.5 text-xs font-medium text-primary-700">
        {{ candidates.length }}
      </span>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <AuditCandidateCard
        v-for="c in sortedCandidates"
        :key="c.candidate_id"
        :candidate="c"
        :is-selected="c.candidate_id === selectedId"
        @click="handleSelect(c.candidate_id)"
      />
    </div>
  </div>
</template>
