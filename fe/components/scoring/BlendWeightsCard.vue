<script setup lang="ts">
import type { WeightSnapshot } from '~/composables/useScoringFactors'

defineProps<{
  blend: WeightSnapshot['blend']
  changed: boolean
}>()
</script>

<template>
  <div class="bg-gray-50 rounded-lg p-4">
    <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Blend Weights</h4>
    <div class="grid grid-cols-2 gap-3">
      <div class="text-center">
        <p class="text-xs text-gray-400 mb-1">Baseline</p>
        <div class="flex items-center justify-center gap-1.5">
          <span class="text-sm font-semibold text-gray-700">{{ (blend.baseline.rule_engine * 100).toFixed(0) }}%</span>
          <span class="text-xs text-gray-400">rules</span>
          <span class="text-gray-300 mx-0.5">/</span>
          <span class="text-sm font-semibold text-gray-700">{{ (blend.baseline.investigators * 100).toFixed(0) }}%</span>
          <span class="text-xs text-gray-400">agents</span>
        </div>
      </div>
      <div class="text-center">
        <p class="text-xs mb-1" :class="changed ? 'text-amber-500 font-medium' : 'text-gray-400'">
          {{ changed ? 'Adjusted' : 'Customer' }}
        </p>
        <div class="flex items-center justify-center gap-1.5">
          <span class="text-sm font-semibold" :class="changed ? 'text-amber-700' : 'text-gray-700'">{{ (blend.customer.rule_engine * 100).toFixed(0) }}%</span>
          <span class="text-xs text-gray-400">rules</span>
          <span class="text-gray-300 mx-0.5">/</span>
          <span class="text-sm font-semibold" :class="changed ? 'text-amber-700' : 'text-gray-700'">{{ (blend.customer.investigators * 100).toFixed(0) }}%</span>
          <span class="text-xs text-gray-400">agents</span>
        </div>
      </div>
    </div>
  </div>
</template>
