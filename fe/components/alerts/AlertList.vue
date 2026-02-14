<script setup lang="ts">
import type { Alert } from '~/utils/alertTypes'
import { INDICATOR_LABELS } from '~/utils/alertTypes'
import { formatCurrency } from '~/utils/formatters'

const props = defineProps<{
  alerts: Alert[]
  riskColor: (score: number) => string
  typeBadge: (type: string) => string
  relativeTime: (ts: string) => string
}>()

function riskLevelBadge(level: string | undefined): string {
  if (!level) return ''
  if (level === 'high' || level === 'critical') return 'bg-red-100 text-red-700'
  if (level === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-green-100 text-green-700'
}

async function handleClick(alert: Alert) {
  if (!alert.read) {
    alert.read = true
    try {
      await $fetch('/api/alerts/read', {
        method: 'PATCH',
        body: { alert_ids: [alert.id] },
      })
    } catch {
      // optimistic update already applied
    }
  }
  const status = alert.type === 'escalation' ? 'escalated' : 'blocked'
  await navigateTo({
    path: '/withdrawals',
    query: { search: alert.customer_name, status },
  })
}

// Show same limited set as notification dropdown
const visibleAlerts = computed(() => props.alerts.slice(0, 8))
</script>

<template>
  <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
    <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
      <h2 class="text-sm font-semibold text-gray-700">Notifications</h2>
      <span class="text-xs text-gray-400">{{ visibleAlerts.length }} alerts</span>
    </div>

    <div v-if="visibleAlerts.length === 0" class="flex h-40 items-center justify-center text-sm text-gray-400">
      No active alerts
    </div>

    <div v-else class="divide-y divide-gray-100">
      <div
        v-for="alert in visibleAlerts"
        :key="alert.id"
        :class="['flex items-start gap-3 px-4 py-3 transition-colors hover:bg-gray-50 cursor-pointer', !alert.read && 'bg-blue-50/30']"
        @click="handleClick(alert)"
      >
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <span class="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="typeBadge(alert.type)">{{ alert.type }}</span>
            <span :class="['text-sm text-gray-800', !alert.read ? 'font-semibold' : 'font-medium']">{{ alert.customer_name }}</span>
            <span v-if="!alert.read" class="h-2 w-2 shrink-0 rounded-full bg-blue-500" />
          </div>
          <p class="mt-0.5 text-xs text-gray-400">{{ alert.account_id }}</p>

          <div class="mt-1.5 flex flex-wrap items-center gap-1">
            <span
              v-if="alert.risk_level"
              class="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase"
              :class="riskLevelBadge(alert.risk_level)"
            >
              {{ alert.risk_level }}
            </span>
            <span
              v-for="ind in alert.indicators.slice(0, 2)"
              :key="ind.name"
              class="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600"
            >
              {{ INDICATOR_LABELS[ind.name] || ind.name }}: {{ ind.score }}
            </span>
          </div>

          <p v-if="alert.reason" class="mt-1 truncate text-[11px] text-gray-500" :title="alert.reason">
            {{ alert.reason.length > 60 ? `${alert.reason.slice(0, 60)}...` : alert.reason }}
          </p>
        </div>

        <div class="shrink-0 text-right">
          <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold" :class="riskColor(alert.risk_score)">{{ alert.risk_score }}</span>
          <p class="mt-1 text-[11px] text-gray-400">{{ relativeTime(alert.timestamp) }}</p>
          <p class="text-xs font-medium text-gray-700">{{ formatCurrency(alert.amount, alert.currency) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
