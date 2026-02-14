<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { formatCurrency, formatDate } from '~/utils/formatters'

useHead({ title: 'Alerts - Nexa' })

interface Alert {
  id: string
  type: 'escalation' | 'block'
  customer_name: string
  account_id: string
  risk_score: number
  indicators: { name: string; score: number }[]
  timestamp: string
  read: boolean
  amount: number
  currency: string
}

interface FraudPattern {
  name: string
  key: string
  accounts_affected: number
  total_exposure: number
  confidence: number
}

const { data: alertsData, refresh } = useApi<{ alerts: Alert[]; total: number }>('/alerts')

const mockAlerts: Alert[] = [
  { id: 'ALT-001', type: 'block', customer_name: 'Sarah Ahmed', account_id: 'ACC-6637', risk_score: 96, indicators: [{ name: 'amount_anomaly', score: 95 }, { name: 'trading_behavior', score: 92 }, { name: 'velocity', score: 88 }], timestamp: new Date(Date.now() - 120000).toISOString(), read: false, amount: 2300, currency: 'USD' },
  { id: 'ALT-002', type: 'escalation', customer_name: 'Marcus Chen', account_id: 'ACC-8821', risk_score: 94, indicators: [{ name: 'amount_anomaly', score: 91 }, { name: 'geographic', score: 85 }, { name: 'device_fingerprint', score: 78 }], timestamp: new Date(Date.now() - 300000).toISOString(), read: false, amount: 4900, currency: 'USD' },
  { id: 'ALT-003', type: 'block', customer_name: 'David Park', account_id: 'ACC-9102', risk_score: 92, indicators: [{ name: 'velocity', score: 94 }, { name: 'geographic', score: 89 }, { name: 'payment_method', score: 76 }], timestamp: new Date(Date.now() - 600000).toISOString(), read: false, amount: 7800, currency: 'USD' },
  { id: 'ALT-004', type: 'escalation', customer_name: 'Elena Petrov', account_id: 'ACC-7744', risk_score: 89, indicators: [{ name: 'payment_method', score: 92 }, { name: 'geographic', score: 87 }, { name: 'card_errors', score: 71 }], timestamp: new Date(Date.now() - 900000).toISOString(), read: true, amount: 3650, currency: 'USD' },
  { id: 'ALT-005', type: 'escalation', customer_name: 'Yuki Tanaka', account_id: 'ACC-5540', risk_score: 91, indicators: [{ name: 'card_errors', score: 93 }, { name: 'velocity', score: 82 }, { name: 'payment_method', score: 79 }], timestamp: new Date(Date.now() - 1500000).toISOString(), read: true, amount: 22100, currency: 'USD' },
  { id: 'ALT-006', type: 'block', customer_name: 'James Wilson', account_id: 'ACC-5519', risk_score: 85, indicators: [{ name: 'trading_behavior', score: 88 }, { name: 'amount_anomaly', score: 82 }, { name: 'recipient', score: 74 }], timestamp: new Date(Date.now() - 2400000).toISOString(), read: true, amount: 6200, currency: 'USD' },
]

const alerts = computed(() => alertsData.value?.alerts ?? mockAlerts)

const selectedIds = ref<Set<string>>(new Set())
const selectedAlert = ref<Alert | null>(null)
const showDetail = ref(false)
const bulkLoading = ref(false)

const fraudPatterns: FraudPattern[] = [
  { name: 'No Trade Pattern', key: 'no_trade', accounts_affected: 12, total_exposure: 45800, confidence: 94 },
  { name: 'Short Trade Abuse', key: 'short_trade', accounts_affected: 8, total_exposure: 23400, confidence: 87 },
  { name: 'Card Testing', key: 'card_testing', accounts_affected: 5, total_exposure: 2100, confidence: 91 },
  { name: 'Velocity Abuse', key: 'velocity', accounts_affected: 3, total_exposure: 67200, confidence: 78 },
]

const escalationCount = computed(() => alerts.value.filter(a => a.type === 'escalation').length)
const blockCount = computed(() => alerts.value.filter(a => a.type === 'block').length)
const unreadCount = computed(() => alerts.value.filter(a => !a.read).length)

function riskColor(score: number) {
  if (score >= 80) return 'text-red-600 bg-red-50'
  if (score >= 50) return 'text-amber-600 bg-amber-50'
  return 'text-green-600 bg-green-50'
}

function typeBadge(type: string) {
  return type === 'block'
    ? 'bg-red-100 text-red-700'
    : 'bg-amber-100 text-amber-700'
}

function toggleSelect(id: string) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

function toggleAll() {
  if (selectedIds.value.size === alerts.value.length) {
    selectedIds.value.clear()
  } else {
    selectedIds.value = new Set(alerts.value.map(a => a.id))
  }
}

function openDetail(alert: Alert) {
  selectedAlert.value = alert
  showDetail.value = true
}

async function bulkAction(action: string) {
  if (selectedIds.value.size === 0) return
  bulkLoading.value = true
  try {
    await $fetch('/api/alerts/bulk-action', {
      method: 'POST',
      body: { alert_ids: Array.from(selectedIds.value), action },
    })
    selectedIds.value.clear()
    await refresh()
  } finally {
    bulkLoading.value = false
  }
}

function relativeTime(ts: string) {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return formatDate(ts, 'MMM dd')
}

const indicatorLabels: Record<string, string> = {
  amount_anomaly: 'Amount Anomaly',
  velocity: 'Velocity',
  payment_method: 'Payment Method',
  geographic: 'Geographic',
  device_fingerprint: 'Device Fingerprint',
  trading_behavior: 'Trading Behavior',
  recipient: 'Recipient Risk',
  card_errors: 'Card Errors',
}

const patternIcons: Record<string, string> = {
  no_trade: 'lucide:ban',
  short_trade: 'lucide:timer',
  card_testing: 'lucide:credit-card',
  velocity: 'lucide:gauge',
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Alerts & Fraud Detection</h1>
        <p class="mt-1 text-sm text-gray-500">Real-time fraud detection and incident response</p>
      </div>
      <CommonNotificationDropdown />
    </div>

    <!-- Summary Bar -->
    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <Icon icon="lucide:alert-triangle" class="h-6 w-6 text-amber-600" />
        <div>
          <p class="text-2xl font-bold text-amber-700">{{ escalationCount }}</p>
          <p class="text-xs text-amber-600">Escalation Alerts</p>
        </div>
      </div>
      <div class="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
        <Icon icon="lucide:shield-off" class="h-6 w-6 text-red-600" />
        <div>
          <p class="text-2xl font-bold text-red-700">{{ blockCount }}</p>
          <p class="text-xs text-red-600">Block Alerts</p>
        </div>
      </div>
      <div class="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
        <Icon icon="lucide:mail" class="h-6 w-6 text-blue-600" />
        <div>
          <p class="text-2xl font-bold text-blue-700">{{ unreadCount }}</p>
          <p class="text-xs text-blue-600">Unread Alerts</p>
        </div>
      </div>
    </div>

    <!-- Bulk Actions -->
    <div v-if="selectedIds.size > 0" class="mb-4 flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <span class="text-sm font-medium text-gray-700">{{ selectedIds.size }} selected</span>
      <div class="flex gap-2">
        <button
          class="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
          :disabled="bulkLoading"
          @click="bulkAction('lock_accounts')"
        >
          <Icon icon="lucide:lock" class="mr-1 inline h-3.5 w-3.5" />
          Lock Accounts
        </button>
        <button
          class="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          :disabled="bulkLoading"
          @click="bulkAction('freeze_withdrawals')"
        >
          <Icon icon="lucide:snowflake" class="mr-1 inline h-3.5 w-3.5" />
          Freeze Withdrawals
        </button>
        <button
          class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
          @click="bulkAction('export')"
        >
          <Icon icon="lucide:download" class="mr-1 inline h-3.5 w-3.5" />
          Export
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <!-- Alerts List -->
      <div class="xl:col-span-2">
        <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h2 class="text-sm font-semibold text-gray-700">Active Alerts</h2>
            <label class="flex items-center gap-2 text-xs text-gray-500">
              <input type="checkbox" class="rounded" :checked="selectedIds.size === alerts.length && alerts.length > 0" @change="toggleAll" />
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
              :class="['flex items-start gap-3 px-4 py-3 transition-colors hover:bg-gray-50 cursor-pointer', !alert.read && 'bg-blue-50/30']"
              @click="openDetail(alert)"
            >
              <input
                type="checkbox"
                class="mt-1 rounded"
                :checked="selectedIds.has(alert.id)"
                @click.stop
                @change="toggleSelect(alert.id)"
              />

              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="typeBadge(alert.type)">
                    {{ alert.type }}
                  </span>
                  <span class="text-sm font-medium text-gray-800">{{ alert.customer_name }}</span>
                  <span class="text-xs text-gray-400">{{ alert.account_id }}</span>
                  <span v-if="!alert.read" class="h-2 w-2 rounded-full bg-blue-500" />
                </div>

                <div class="mt-1 flex flex-wrap gap-1">
                  <span
                    v-for="ind in alert.indicators.slice(0, 3)"
                    :key="ind.name"
                    class="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600"
                  >
                    {{ indicatorLabels[ind.name] || ind.name }}: {{ ind.score }}
                  </span>
                </div>
              </div>

              <div class="shrink-0 text-right">
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold" :class="riskColor(alert.risk_score)">
                  {{ alert.risk_score }}
                </span>
                <p class="mt-1 text-xs text-gray-400">{{ relativeTime(alert.timestamp) }}</p>
                <p class="text-xs font-medium text-gray-700">{{ formatCurrency(alert.amount, alert.currency) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Fraud Pattern Cards -->
      <div class="space-y-4">
        <h2 class="text-sm font-semibold text-gray-700">Detected Fraud Patterns</h2>
        <div
          v-for="pattern in fraudPatterns"
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
    </div>

    <!-- Alert Detail Modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="showDetail && selectedAlert" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" @click.self="showDetail = false">
          <div class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-bold text-gray-900">Alert Details</h3>
              <button class="rounded-lg p-1 hover:bg-gray-100" @click="showDetail = false">
                <Icon icon="lucide:x" class="h-5 w-5 text-gray-500" />
              </button>
            </div>

            <div class="mt-4 space-y-4">
              <!-- Customer Info -->
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-sm font-semibold text-gray-800">{{ selectedAlert.customer_name }}</p>
                <p class="text-xs text-gray-500">Account: {{ selectedAlert.account_id }}</p>
                <div class="mt-2 flex items-center gap-2">
                  <span class="rounded px-1.5 py-0.5 text-xs font-bold uppercase" :class="typeBadge(selectedAlert.type)">{{ selectedAlert.type }}</span>
                  <span class="rounded-full px-2 py-0.5 text-xs font-bold" :class="riskColor(selectedAlert.risk_score)">Risk: {{ selectedAlert.risk_score }}</span>
                </div>
              </div>

              <!-- Transaction -->
              <div>
                <p class="text-xs font-semibold text-gray-500 uppercase">Triggered By</p>
                <p class="text-sm text-gray-700">Withdrawal of <span class="font-bold">{{ formatCurrency(selectedAlert.amount, selectedAlert.currency) }}</span></p>
                <p class="text-xs text-gray-400">{{ formatDate(selectedAlert.timestamp) }}</p>
              </div>

              <!-- Indicator Scores -->
              <div>
                <p class="mb-2 text-xs font-semibold text-gray-500 uppercase">Indicator Scores</p>
                <div class="space-y-2">
                  <div v-for="ind in selectedAlert.indicators" :key="ind.name" class="flex items-center gap-2">
                    <span class="w-28 truncate text-xs text-gray-600">{{ indicatorLabels[ind.name] || ind.name }}</span>
                    <div class="h-1.5 flex-1 rounded-full bg-gray-100">
                      <div
                        class="h-1.5 rounded-full transition-all"
                        :class="ind.score >= 80 ? 'bg-red-500' : ind.score >= 50 ? 'bg-amber-500' : 'bg-green-500'"
                        :style="{ width: `${ind.score}%` }"
                      />
                    </div>
                    <span class="w-8 text-right text-xs font-semibold" :class="ind.score >= 80 ? 'text-red-600' : ind.score >= 50 ? 'text-amber-600' : 'text-green-600'">{{ ind.score }}</span>
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex gap-2 pt-2">
                <button class="flex-1 rounded-lg bg-primary-600 py-2 text-sm font-medium text-white hover:bg-primary-700">
                  View Customer
                </button>
                <button class="flex-1 rounded-lg border border-red-300 py-2 text-sm font-medium text-red-600 hover:bg-red-50">
                  Lock Account
                </button>
                <button class="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-500 hover:bg-gray-50" @click="showDetail = false">
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
