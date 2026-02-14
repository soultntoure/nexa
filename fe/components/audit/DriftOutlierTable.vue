<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { useDriftActions } from '~/composables/useDriftActions'

interface Outlier {
  customer_id: string
  indicator_name: string
  indicator_label?: string
  multiplier: number
  deviation: number
}

defineProps<{ outliers: Outlier[] }>()

const { resetCustomer, isApplied } = useDriftActions()

function deviationLabel(d: number): string {
  if (d > 1.0) return 'Far from normal'
  if (d > 0.5) return 'Moderately off'
  return 'Slightly off'
}

function deviationColor(d: number): string {
  if (d > 1.0) return 'text-red-600'
  if (d > 0.5) return 'text-amber-600'
  return 'text-gray-600'
}

async function handleReset(customerId: string): Promise<void> {
  try { await resetCustomer(customerId) } catch { /* toast */ }
}
</script>

<template>
  <div v-if="outliers.length">
    <h3 class="mb-2 text-sm font-semibold text-gray-700">Affected Customers</h3>
    <p class="mb-3 text-xs text-gray-400">
      These customers have signal weights that have shifted significantly from the norm.
      Resetting returns their weights to the default baseline.
    </p>
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-gray-200 text-xs text-gray-500">
          <tr>
            <th class="pb-2 pr-4">Customer</th>
            <th class="pb-2 pr-4">Signal</th>
            <th class="pb-2 pr-4">Current Weight</th>
            <th class="pb-2 pr-4">How far off</th>
            <th class="pb-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(o, i) in outliers.slice(0, 20)" :key="i" class="border-b border-gray-100">
            <td class="py-2 pr-4 font-mono text-xs text-gray-800">{{ o.customer_id.slice(0, 12) }}</td>
            <td class="py-2 pr-4 text-gray-600">{{ o.indicator_label ?? o.indicator_name }}</td>
            <td class="py-2 pr-4 font-medium" :class="o.multiplier > 2 ? 'text-red-600' : o.multiplier < 0.5 ? 'text-amber-600' : 'text-gray-800'">
              {{ o.multiplier.toFixed(1) }}x
            </td>
            <td class="py-2 pr-4" :class="deviationColor(o.deviation)">
              {{ deviationLabel(o.deviation) }}
            </td>
            <td class="py-2">
              <div v-if="isApplied(`reset:${o.customer_id}`)" class="flex items-center gap-1 text-green-600 text-xs">
                <Icon icon="lucide:check" class="h-4 w-4" /> Reset done
              </div>
              <button
                v-else
                class="rounded bg-orange-50 px-2 py-1 text-xs text-orange-700 hover:bg-orange-100"
                @click="handleReset(o.customer_id)"
              >Reset to Baseline</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
