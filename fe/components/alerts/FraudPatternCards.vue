<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { FraudPattern } from '~/utils/alertTypes'
import { formatCurrency } from '~/utils/formatters'

defineProps<{
  patterns: FraudPattern[]
  patternIcons: Record<string, string>
}>()
</script>

<template>
  <div class="space-y-4">
    <h2 class="text-sm font-semibold text-gray-700">Detected Fraud Patterns</h2>
    <div
      v-for="pattern in patterns"
      :key="pattern.key"
      class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div class="flex items-center gap-2">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50">
          <Icon :icon="patternIcons[pattern.key] || 'lucide:alert-circle'" class="h-4 w-4 text-primary-600" />
        </div>
        <h3 class="text-sm font-semibold text-gray-800">{{ pattern.name }}</h3>
      </div>
      <div class="mt-3 grid grid-cols-3 gap-2 text-center">
        <div>
          <p class="text-lg font-bold text-gray-900">{{ pattern.accounts_affected }}</p>
          <p class="text-[10px] text-gray-400">Accounts</p>
        </div>
        <div>
          <p class="text-lg font-bold text-gray-900">{{ formatCurrency(pattern.total_exposure) }}</p>
          <p class="text-[10px] text-gray-400">Exposure</p>
        </div>
        <div>
          <p class="text-lg font-bold" :class="pattern.confidence >= 90 ? 'text-red-600' : 'text-amber-600'">{{ pattern.confidence }}%</p>
          <p class="text-[10px] text-gray-400">Confidence</p>
        </div>
      </div>
    </div>
  </div>
</template>
