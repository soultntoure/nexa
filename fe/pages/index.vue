<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { formatCurrency, formatDate } from '~/utils/formatters'

useHead({ title: 'Dashboard - Nexa' })

interface DashboardStats {
  total_payouts_today: number
  total_payout_amount: number
  auto_approved_rate: number
  auto_approved_trend: number
  pending_review_count: number
  active_alerts: number
  alert_severity: { high: number; medium: number; low: number }
  risk_distribution: { approved: number; escalated: number; blocked: number }
  top_risk_indicators: { name: string; count: number }[]
  recent_activity: {
    id: string
    action: string
    amount: number
    currency: string
    timestamp: string
    customer_id: string
  }[]
  avg_decision_time_seconds: number
}

const defaultStats: DashboardStats = {
  total_payouts_today: 847,
  total_payout_amount: 1243650.00,
  auto_approved_rate: 73.2,
  auto_approved_trend: 4.7,
  pending_review_count: 23,
  active_alerts: 12,
  alert_severity: { high: 3, medium: 5, low: 4 },
  risk_distribution: { approved: 621, escalated: 157, blocked: 69 },
  top_risk_indicators: [
    { name: 'amount_anomaly', count: 89 },
    { name: 'velocity', count: 67 },
    { name: 'geographic', count: 54 },
    { name: 'trading_behavior', count: 48 },
    { name: 'payment_method', count: 41 },
    { name: 'device_fingerprint', count: 33 },
    { name: 'recipient', count: 27 },
    { name: 'card_errors', count: 19 },
  ],
  recent_activity: [
    { id: 'TXN-001', action: 'auto-approved', amount: 250.00, currency: 'USD', timestamp: '2026-02-08T10:00:00Z', customer_id: 'Marcus Chen (ACC-8821)' },
    { id: 'TXN-002', action: 'blocked', amount: 4900.00, currency: 'USD', timestamp: '2026-02-08T09:55:00Z', customer_id: 'Sarah Ahmed (ACC-6637)' },
    { id: 'TXN-003', action: 'auto-approved', amount: 175.50, currency: 'USD', timestamp: '2026-02-08T09:52:00Z', customer_id: 'John Riley (ACC-3301)' },
    { id: 'TXN-004', action: 'escalated', amount: 3200.00, currency: 'USD', timestamp: '2026-02-08T09:50:00Z', customer_id: 'Elena Petrov (ACC-7744)' },
    { id: 'TXN-005', action: 'auto-approved', amount: 89.99, currency: 'USD', timestamp: '2026-02-08T09:45:00Z', customer_id: 'Lisa Wong (ACC-2210)' },
    { id: 'TXN-006', action: 'blocked', amount: 7800.00, currency: 'USD', timestamp: '2026-02-08T09:40:00Z', customer_id: 'David Park (ACC-9102)' },
    { id: 'TXN-007', action: 'auto-approved', amount: 420.00, currency: 'USD', timestamp: '2026-02-08T09:35:00Z', customer_id: 'Nina Torres (ACC-4455)' },
    { id: 'TXN-008', action: 'escalated', amount: 1650.00, currency: 'USD', timestamp: '2026-02-08T09:30:00Z', customer_id: 'Yuki Tanaka (ACC-5540)' },
  ],
  avg_decision_time_seconds: 0.3,
}

const stats = ref<DashboardStats>(defaultStats)
const loadingApi = ref(false)

if (import.meta.client) {
  loadingApi.value = true
  $fetch('/api/dashboard/stats')
    .then((data: any) => {
      if (data) stats.value = data
    })
    .catch(() => {})
    .finally(() => { loadingApi.value = false })
}

const status = computed(() => loadingApi.value ? 'pending' : 'success')

const riskIndicatorLabels: Record<string, string> = {
  amount_anomaly: 'Amount Anomaly',
  velocity: 'Velocity',
  payment_method: 'Payment Method',
  geographic: 'Geographic',
  device_fingerprint: 'Device Fingerprint',
  trading_behavior: 'Trading Behavior',
  recipient: 'Recipient Risk',
  card_errors: 'Card Errors',
}

const actionColors: Record<string, string> = {
  'auto-approved': 'text-green-600 bg-green-50',
  approved: 'text-green-600 bg-green-50',
  escalated: 'text-amber-600 bg-amber-50',
  blocked: 'text-red-600 bg-red-50',
}

const actionIcons: Record<string, string> = {
  'auto-approved': 'lucide:check-circle',
  approved: 'lucide:check-circle',
  escalated: 'lucide:alert-triangle',
  blocked: 'lucide:shield-off',
}

const riskDistTotal = computed(() => {
  if (!stats.value) return 1
  const d = stats.value.risk_distribution
  return d.approved + d.escalated + d.blocked || 1
})

function riskPct(val: number) {
  return ((val / riskDistTotal.value) * 100).toFixed(1)
}

function indicatorMaxCount() {
  if (!stats.value?.top_risk_indicators?.length) return 1
  return Math.max(...stats.value.top_risk_indicators.map(i => i.count)) || 1
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p class="mt-1 text-sm text-gray-500">AI-Powered Payments Approval & Fraud Intelligence</p>
      </div>
      <CommonNotificationDropdown />
    </div>

    <template v-if="stats">
      <!-- Stats Cards -->
      <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <!-- Total Payouts Today -->
        <div class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-medium text-gray-500">Total Payouts Today</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.total_payouts_today }}</p>
          <p class="text-xs text-gray-400">{{ formatCurrency(stats.total_payout_amount) }}</p>
        </div>

        <!-- Auto-Approved Rate -->
        <div class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-medium text-gray-500">Auto-Approved Rate</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.auto_approved_rate }}%</p>
          <p class="flex items-center gap-1 text-xs" :class="stats.auto_approved_trend >= 0 ? 'text-green-600' : 'text-red-600'">
            <Icon :icon="stats.auto_approved_trend >= 0 ? 'lucide:trending-up' : 'lucide:trending-down'" class="h-3 w-3" />
            {{ Math.abs(stats.auto_approved_trend) }}% vs yesterday
          </p>
        </div>

        <!-- Pending Review -->
        <div class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-medium text-gray-500">Pending Review</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.pending_review_count }}</p>
          <p v-if="stats.pending_review_count > 10" class="text-xs font-medium text-amber-600">
            Needs attention
          </p>
          <p v-else class="text-xs text-gray-400">In queue</p>
        </div>

        <!-- Active Alerts -->
        <div class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-medium text-gray-500">Active Alerts</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.active_alerts }}</p>
          <div class="flex items-center gap-2 text-xs">
            <span class="text-red-600">{{ stats.alert_severity.high }}H</span>
            <span class="text-amber-600">{{ stats.alert_severity.medium }}M</span>
            <span class="text-gray-400">{{ stats.alert_severity.low }}L</span>
          </div>
        </div>
      </div>

      <!-- Middle Row: Risk Distribution + Processing Time -->
      <div class="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- Risk Distribution -->
        <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2">
          <h2 class="mb-4 text-sm font-semibold text-gray-700">Risk Score Distribution</h2>
          <div class="flex items-center gap-8">
            <!-- Donut chart (CSS-based) -->
            <div class="relative h-40 w-40 shrink-0">
              <svg viewBox="0 0 36 36" class="h-full w-full -rotate-90">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle
                  cx="18" cy="18" r="15.9" fill="none"
                  stroke="#22c55e" stroke-width="3"
                  :stroke-dasharray="`${riskPct(stats.risk_distribution.approved)} ${100 - Number(riskPct(stats.risk_distribution.approved))}`"
                  stroke-dashoffset="0"
                />
                <circle
                  cx="18" cy="18" r="15.9" fill="none"
                  stroke="#f59e0b" stroke-width="3"
                  :stroke-dasharray="`${riskPct(stats.risk_distribution.escalated)} ${100 - Number(riskPct(stats.risk_distribution.escalated))}`"
                  :stroke-dashoffset="`-${riskPct(stats.risk_distribution.approved)}`"
                />
                <circle
                  cx="18" cy="18" r="15.9" fill="none"
                  stroke="#ef4444" stroke-width="3"
                  :stroke-dasharray="`${riskPct(stats.risk_distribution.blocked)} ${100 - Number(riskPct(stats.risk_distribution.blocked))}`"
                  :stroke-dashoffset="`-${Number(riskPct(stats.risk_distribution.approved)) + Number(riskPct(stats.risk_distribution.escalated))}`"
                />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ riskDistTotal }}</span>
                <span class="text-xs text-gray-400">Total</span>
              </div>
            </div>
            <!-- Legend -->
            <div class="space-y-3">
              <div class="flex items-center gap-2">
                <span class="h-3 w-3 rounded-full bg-green-500" />
                <span class="text-sm text-gray-600">Approved</span>
                <span class="ml-auto text-sm font-semibold text-gray-900">{{ stats.risk_distribution.approved }}</span>
                <span class="text-xs text-gray-400">({{ riskPct(stats.risk_distribution.approved) }}%)</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="h-3 w-3 rounded-full bg-amber-500" />
                <span class="text-sm text-gray-600">Escalated</span>
                <span class="ml-auto text-sm font-semibold text-gray-900">{{ stats.risk_distribution.escalated }}</span>
                <span class="text-xs text-gray-400">({{ riskPct(stats.risk_distribution.escalated) }}%)</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="h-3 w-3 rounded-full bg-red-500" />
                <span class="text-sm text-gray-600">Blocked</span>
                <span class="ml-auto text-sm font-semibold text-gray-900">{{ stats.risk_distribution.blocked }}</span>
                <span class="text-xs text-gray-400">({{ riskPct(stats.risk_distribution.blocked) }}%)</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Processing Time -->
        <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 class="mb-4 text-sm font-semibold text-gray-700">Avg Decision Time</h2>
          <div class="flex flex-col items-center justify-center py-4">
            <div class="flex items-baseline gap-1">
              <span class="text-5xl font-bold text-gray-900">{{ stats.avg_decision_time_seconds.toFixed(1) }}</span>
              <span class="text-lg text-gray-400">s</span>
            </div>
            <p class="mt-2 text-sm text-gray-500">Per transaction</p>
            <div class="mt-4 flex items-center gap-2 rounded-full bg-green-50 px-3 py-1">
              <Icon icon="lucide:zap" class="h-4 w-4 text-green-600" />
              <span class="text-xs font-medium text-green-700">Real-time processing</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Row: Top Risk Indicators + Recent Activity -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Top Risk Indicators -->
        <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 class="mb-4 text-sm font-semibold text-gray-700">Top Risk Indicators</h2>
          <div class="space-y-3">
            <div
              v-for="indicator in stats.top_risk_indicators"
              :key="indicator.name"
              class="flex items-center gap-3"
            >
              <span class="w-32 truncate text-sm text-gray-600">
                {{ riskIndicatorLabels[indicator.name] || indicator.name }}
              </span>
              <div class="flex-1">
                <div class="h-2 rounded-full bg-gray-100">
                  <div
                    class="h-2 rounded-full bg-primary-500 transition-all"
                    :style="{ width: `${(indicator.count / indicatorMaxCount()) * 100}%` }"
                  />
                </div>
              </div>
              <span class="w-8 text-right text-sm font-semibold text-gray-700">{{ indicator.count }}</span>
            </div>
          </div>
        </div>

        <!-- Recent Activity Feed -->
        <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 class="mb-4 text-sm font-semibold text-gray-700">Recent Activity</h2>
          <div class="space-y-3">
            <div
              v-for="activity in stats.recent_activity?.slice(0, 8)"
              :key="activity.id"
              class="flex items-center gap-3 rounded-lg border border-gray-100 px-3 py-2"
            >
              <div
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                :class="actionColors[activity.action] || 'text-gray-600 bg-gray-50'"
              >
                <Icon
                  :icon="actionIcons[activity.action] || 'lucide:circle'"
                  class="h-4 w-4"
                />
              </div>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-gray-800">
                  {{ activity.customer_id }}
                </p>
                <p class="text-xs text-gray-400">{{ formatDate(activity.timestamp) }}</p>
              </div>
              <div class="text-right">
                <p class="text-sm font-semibold text-gray-900">{{ formatCurrency(activity.amount, activity.currency) }}</p>
                <span
                  class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold capitalize"
                  :class="actionColors[activity.action] || 'text-gray-600 bg-gray-50'"
                >
                  {{ activity.action }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Demo mode indicator -->
    <div v-if="status === 'error'" class="mt-4 flex items-center justify-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700">
      <Icon icon="lucide:info" class="h-4 w-4" />
      Demo mode - showing sample data. Connect backend API for live data.
    </div>
  </div>
</template>
