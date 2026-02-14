<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Alert } from '~/utils/alertTypes'
import { INDICATOR_LABELS } from '~/utils/alertTypes'
import { formatCurrency } from '~/utils/formatters'

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const alerts = ref<Alert[]>([])

let pollTimer: ReturnType<typeof setInterval> | null = null

const unreadCount = computed(() => alerts.value.filter(a => !a.read).length)

function toggle() {
  isOpen.value = !isOpen.value
}

async function handleAlertClick(alert: Alert) {
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
  isOpen.value = false
  const status = alert.type === 'escalation' ? 'escalated' : 'blocked'
  await navigateTo({
    path: '/withdrawals',
    query: { search: alert.customer_name, status },
  })
}

async function markAllRead() {
  const unreadIds = alerts.value.filter(a => !a.read).map(a => a.id)
  if (!unreadIds.length) return
  alerts.value.forEach(a => { a.read = true })
  try {
    await $fetch('/api/alerts/read', {
      method: 'PATCH',
      body: { alert_ids: unreadIds },
    })
  } catch {
    // optimistic update already applied
  }
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

async function fetchAlerts() {
  try {
    const data = await $fetch<{ alerts: Alert[] }>('/api/alerts')
    alerts.value = (data.alerts ?? []).slice(0, 8)
  } catch {
    // keep existing alerts on error
  }
}

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function riskColor(score: number): string {
  if (score >= 80) return 'bg-red-100 text-red-700'
  if (score >= 50) return 'bg-amber-100 text-amber-700'
  return 'bg-green-100 text-green-700'
}

function typeBadge(type: string): string {
  if (type === 'block') return 'bg-red-100 text-red-700'
  if (type === 'card_lockdown') return 'bg-orange-100 text-orange-700'
  return 'bg-amber-100 text-amber-700'
}

function riskLevelBadge(level: string | undefined): string {
  if (!level) return ''
  if (level === 'high' || level === 'critical') return 'bg-red-100 text-red-700'
  if (level === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-green-100 text-green-700'
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  fetchAlerts()
  pollTimer = setInterval(fetchAlerts, 5000)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <button
      class="relative rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
      @click="toggle"
    >
      <Icon icon="lucide:bell" class="h-5 w-5" />
      <span
        v-if="unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary-500 text-[10px] font-bold text-white"
      >
        {{ unreadCount > 9 ? '9+' : unreadCount }}
      </span>
    </button>

    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="isOpen"
        class="absolute right-0 mt-2 w-96 rounded-xl border border-gray-200 bg-white shadow-lg"
      >
        <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <h3 class="text-sm font-semibold text-gray-900">Active Alerts</h3>
          <button
            v-if="unreadCount > 0"
            class="text-xs font-medium text-primary-500 hover:text-primary-700"
            @click.stop="markAllRead"
          >
            Mark all read
          </button>
        </div>
        <ul class="max-h-96 overflow-y-auto divide-y divide-gray-100">
          <li
            v-for="alert in alerts"
            :key="alert.id"
            :class="['cursor-pointer px-4 py-3 transition-colors hover:bg-gray-50', !alert.read && 'bg-blue-50/30']"
            @click="handleAlertClick(alert)"
          >
            <div class="flex items-start gap-3">
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
          </li>
          <li v-if="!alerts.length" class="px-4 py-6 text-center text-sm text-gray-400">
            No active alerts
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>
