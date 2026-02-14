<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { IndicatorRow } from '~/composables/useScoringFactors'
import {
  INDICATOR_LABELS, INDICATOR_ICONS,
  multiplierLabel, multiplierStyle, multiplierIcon,
} from '~/composables/useScoringFactors'

defineProps<{
  adjusted: IndicatorRow[]
  baseline: IndicatorRow[]
}>()
</script>

<template>
  <!-- Adjusted Indicators -->
  <div v-if="adjusted.length">
    <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Weight Adjustments</h4>
    <div class="space-y-2">
      <div
        v-for="row in adjusted"
        :key="row.name"
        class="border border-gray-200 rounded-lg p-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Icon :icon="INDICATOR_ICONS[row.name] || 'lucide:activity'" class="w-4 h-4 text-gray-400" />
            <span class="text-sm font-medium text-gray-800">{{ INDICATOR_LABELS[row.name] || row.name }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs tabular-nums text-gray-400">{{ row.baseline_weight.toFixed(2) }} &rarr; {{ row.customer_weight.toFixed(2) }}</span>
            <span
              class="inline-flex items-center gap-0.5 px-2 py-0.5 text-xs font-bold rounded-full"
              :class="multiplierStyle(row.customer_multiplier)"
            >
              <Icon :icon="multiplierIcon(row.customer_multiplier)" class="w-3 h-3" />
              {{ multiplierLabel(row.customer_multiplier) }}
            </span>
          </div>
        </div>
        <p v-if="row.reason" class="mt-1.5 text-xs text-gray-500 leading-relaxed pl-6">
          {{ row.reason }}
        </p>
      </div>
    </div>
  </div>

  <!-- Baseline Indicators -->
  <div v-if="baseline.length">
    <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Unchanged (Baseline)</h4>
    <div class="flex flex-wrap gap-2">
      <div
        v-for="row in baseline"
        :key="row.name"
        class="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-50 rounded-md text-xs text-gray-500"
      >
        <Icon :icon="INDICATOR_ICONS[row.name] || 'lucide:activity'" class="w-3.5 h-3.5" />
        {{ INDICATOR_LABELS[row.name] || row.name }}
        <span class="tabular-nums font-medium text-gray-600">{{ row.baseline_weight.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>
