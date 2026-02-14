<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Alert, LinkedAccount } from '~/utils/alertTypes'
import { INDICATOR_LABELS } from '~/utils/alertTypes'
import { formatCurrency } from '~/utils/formatters'

const props = defineProps<{
  alerts: Alert[]
  selectedIds: Set<string>
  cardCheckCache: Record<string, { shared: boolean; linked_count: number; linked_accounts: LinkedAccount[] }>
  riskColor: (score: number) => string
  typeBadge: (type: string) => string
  relativeTime: (ts: string) => string
}>()

const emit = defineEmits<{
  select: [id: string]
  selectAll: []
  openDetail: [alert: Alert]
}>()

function hasSharedCard(alert: Alert): boolean {
  return props.cardCheckCache[alert.account_id]?.shared ?? false
}

function cardCheckDone(alert: Alert): boolean {
  return alert.account_id in props.cardCheckCache
}

function linkedAccountsSummary(alert: Alert): string {
  const linked = props.cardCheckCache[alert.account_id]?.linked_accounts ?? []
  if (linked.length === 0) return ''
  const preview = linked.slice(0, 2).map(a => `${a.customer_name} (${a.customer_id})`)
  return linked.length > 2 ? `${preview.join(', ')} +${linked.length - 2} more` : preview.join(', ')
}
</script>

<template>
  <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
    <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
      <h2 class="text-sm font-semibold text-gray-700">Active Alerts</h2>
      <label class="flex items-center gap-2 text-xs text-gray-500">
        <input type="checkbox" class="rounded" :checked="selectedIds.size === alerts.length && alerts.length > 0" @change="emit('selectAll')" />
        Select All
      </label>
    </div>

    <div v-if="alerts.length === 0" class="flex h-40 items-center justify-center text-sm text-gray-400">
      No active alerts
    </div>

    <div v-else class="divide-y divide-gray-100">
      <div
        v-for="alert in alerts"
        :key="alert.id"
        :class="['flex items-start gap-3 px-4 py-3.5 transition-colors hover:bg-gray-50 cursor-pointer', !alert.read && 'bg-blue-50/30']"
        @click="emit('openDetail', alert)"
      >
        <input
          type="checkbox"
          class="mt-1 rounded"
          :checked="selectedIds.has(alert.id)"
          @click.stop
          @change="emit('select', alert.id)"
        />

        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <span class="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="typeBadge(alert.type)">{{ alert.type }}</span>
            <span class="text-sm font-medium text-gray-800">{{ alert.customer_name }}</span>
            <span class="text-xs text-gray-400">{{ alert.account_id }}</span>
            <span v-if="!alert.read" class="h-2 w-2 rounded-full bg-blue-500" />
          </div>

          <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span
              v-for="ind in alert.indicators.slice(0, 3)"
              :key="ind.name"
              class="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600"
            >
              {{ INDICATOR_LABELS[ind.name] || ind.name }}: {{ ind.score }}
            </span>
            <span
              v-if="cardCheckDone(alert) && hasSharedCard(alert)"
              class="inline-flex items-center gap-0.5 rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-medium text-orange-700"
            >
              <Icon icon="lucide:credit-card" class="h-2.5 w-2.5" />
              Shared card ({{ cardCheckCache[alert.account_id]?.linked_count }})
            </span>
            <span
              v-if="cardCheckDone(alert) && hasSharedCard(alert)"
              class="rounded bg-orange-50 px-1.5 py-0.5 text-[10px] text-orange-700"
            >
              Connected to: {{ linkedAccountsSummary(alert) }}
            </span>
            <span
              v-else-if="cardCheckDone(alert)"
              class="rounded bg-gray-50 px-1.5 py-0.5 text-[10px] text-gray-400"
            >
              No card match
            </span>
          </div>
        </div>

        <div class="shrink-0 text-right">
          <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold" :class="riskColor(alert.risk_score)">{{ alert.risk_score }}</span>
          <p class="mt-1 text-xs text-gray-400">{{ relativeTime(alert.timestamp) }}</p>
          <p class="text-xs font-medium text-gray-700">{{ formatCurrency(alert.amount, alert.currency) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
