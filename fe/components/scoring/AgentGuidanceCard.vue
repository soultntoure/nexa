<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { AgentSignal } from '~/composables/useScoringFactors'
import { INDICATOR_LABELS } from '~/composables/useScoringFactors'

defineProps<{
  boosted: AgentSignal[]
  dampened: AgentSignal[]
  emerging: AgentSignal[]
}>()

const groups = [
  { key: 'boosted', label: 'Boosted — treat as stronger evidence', color: 'red', icon: 'lucide:arrow-up-circle' },
  { key: 'dampened', label: 'Dampened — treat as weaker evidence', color: 'green', icon: 'lucide:arrow-down-circle' },
  { key: 'emerging', label: 'Emerging — trend only, not decisive', color: 'yellow', icon: 'lucide:activity' },
] as const
</script>

<template>
  <div class="bg-violet-50 border border-violet-100 rounded-lg p-4 space-y-3">
    <h4 class="text-xs font-semibold text-violet-600 uppercase tracking-wider flex items-center gap-1.5">
      <Icon icon="lucide:bot" class="w-3.5 h-3.5" />
      Agent Prompt Adjustments
    </h4>

    <template v-for="g in groups" :key="g.key">
      <div v-if="(g.key === 'boosted' ? boosted : g.key === 'dampened' ? dampened : emerging).length">
        <p class="text-[11px] font-medium mb-1" :class="`text-${g.color}-500`">{{ g.label }}</p>
        <div
          v-for="s in (g.key === 'boosted' ? boosted : g.key === 'dampened' ? dampened : emerging)"
          :key="s.name"
          class="flex items-start gap-2 ml-1 mb-1"
        >
          <Icon :icon="g.icon" class="w-3.5 h-3.5 mt-0.5 shrink-0" :class="`text-${g.color}-400`" />
          <p class="text-xs text-gray-700">
            <span class="font-semibold">{{ INDICATOR_LABELS[s.name] || s.name }}</span>
            <span class="ml-1" :class="`text-${g.color}-500`">{{ s.multiplier.toFixed(2) }}x</span>
            <span class="text-gray-400 ml-1">({{ s.direction }} {{ s.pct }}%)</span>
            <span v-if="s.reason" class="text-gray-500 block mt-0.5 pl-0.5">{{ s.reason }}</span>
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
