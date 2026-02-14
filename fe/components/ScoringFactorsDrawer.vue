<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { useScoringFactors, STATUS_BADGE } from '~/composables/useScoringFactors'

const props = defineProps<{
  visible: boolean
  customerId: string
  riskScore: number
  decision: string
}>()

const emit = defineEmits<{ close: [] }>()

const customerIdRef = toRef(props, 'customerId')
const {
  snapshot, loading, error, resetting,
  fetchSnapshot, resetToBaseline,
  adjustedIndicators, baselineIndicators,
  blendChanged, isPersonalized,
  boostedSignals, dampenedSignals, emergingSignals, hasAgentGuidance,
} = useScoringFactors(customerIdRef)

watch(() => props.visible, async (open) => {
  if (open && props.customerId) await fetchSnapshot()
})

const thresholdExplanation = computed(() => {
  const s = props.riskScore
  if (s < 0.3) return `Score ${s.toFixed(2)} is below 0.30 — auto-approved.`
  if (s < 0.7) return `Score ${s.toFixed(2)} is in gray zone (0.30–0.70) — escalated for review.`
  return `Score ${s.toFixed(2)} is at or above 0.70 — auto-blocked.`
})

function handleClose() { emit('close') }
function handleKeydown(e: KeyboardEvent) { if (e.key === 'Escape') handleClose() }
onMounted(() => document.addEventListener('keydown', handleKeydown))
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="translate-x-0"
      leave-to-class="translate-x-full"
    >
      <div v-if="visible" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0" @click="handleClose" />

        <div class="relative w-full max-w-lg bg-white shadow-2xl flex flex-col overflow-hidden">
          <!-- Header -->
          <div class="flex items-center justify-between p-5 border-b border-gray-200 shrink-0">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Scoring Factors</h3>
              <p class="text-xs text-gray-500 mt-0.5">{{ customerId }}</p>
            </div>
            <div class="flex items-center gap-2">
              <span
                v-if="snapshot"
                class="px-2.5 py-1 text-xs font-medium rounded-full"
                :class="[
                  STATUS_BADGE[snapshot.personalization_status]?.bg ?? 'bg-gray-100',
                  STATUS_BADGE[snapshot.personalization_status]?.text ?? 'text-gray-600',
                ]"
              >
                {{ snapshot.personalization_status }}
              </span>
              <button class="p-1.5 hover:bg-gray-100 rounded-lg" @click="handleClose">
                <Icon icon="lucide:x" class="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto p-5 space-y-4">
            <div v-if="loading" class="flex items-center justify-center py-12">
              <div class="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
              <span class="ml-3 text-sm text-gray-500">Loading scoring factors...</span>
            </div>

            <div v-else-if="error" class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p class="text-sm text-yellow-700">{{ error }}</p>
            </div>

            <template v-else-if="snapshot">
              <!-- Threshold -->
              <div class="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3 flex items-start gap-3">
                <Icon icon="lucide:info" class="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                <p class="text-sm text-blue-800">{{ thresholdExplanation }}</p>
              </div>

              <ScoringBlendWeightsCard :blend="snapshot.blend" :changed="blendChanged" />
              <ScoringWeightAdjustmentsList :adjusted="adjustedIndicators" :baseline="baselineIndicators" />
              <ScoringAgentGuidanceCard v-if="hasAgentGuidance" :boosted="boostedSignals" :dampened="dampenedSignals" :emerging="emergingSignals" />

              <!-- Freshness -->
              <div class="text-xs text-gray-400 flex items-center gap-3 pt-1">
                <span v-if="snapshot.last_updated">Updated {{ new Date(snapshot.last_updated).toLocaleString() }}</span>
                <span>{{ snapshot.sample_count }} decision samples</span>
              </div>
            </template>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-gray-200 shrink-0 flex items-center justify-between bg-white">
            <button
              v-if="isPersonalized"
              class="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
              :disabled="resetting"
              @click="resetToBaseline"
            >
              <Icon icon="lucide:rotate-ccw" class="w-4 h-4 inline mr-1" />
              Reset to baseline
            </button>
            <span v-else />
            <button
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              @click="handleClose"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
