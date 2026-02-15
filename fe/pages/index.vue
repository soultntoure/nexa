<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { formatCurrency, formatDate } from '~/utils/formatters'

useHead({ title: 'Nexa' })

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
  new_customers: {
    id: string
    name: string
    email: string
    country: string
    registration_date: string
  }[]
  avg_decision_time_seconds: number
  daily_decision_trend: { date: string; approved: number; escalated: number; blocked: number }[]
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
  new_customers: [
    { id: 'CUST-101', name: 'Alice Rodriguez', email: 'alice.r@example.com', country: 'US', registration_date: '2026-02-15T09:30:00Z' },
    { id: 'CUST-102', name: 'David Kim', email: 'david.kim@example.com', country: 'SG', registration_date: '2026-02-15T08:45:00Z' },
    { id: 'CUST-103', name: 'Maria Santos', email: 'maria.s@example.com', country: 'BR', registration_date: '2026-02-15T07:20:00Z' },
    { id: 'CUST-104', name: 'James Wilson', email: 'j.wilson@example.com', country: 'GB', registration_date: '2026-02-15T06:15:00Z' },
    { id: 'CUST-105', name: 'Yuki Tanaka', email: 'yuki.t@example.com', country: 'JP', registration_date: '2026-02-15T05:00:00Z' },
  ],
  avg_decision_time_seconds: 0.3,
  daily_decision_trend: [
    { date: '2026-02-09', approved: 85, escalated: 12, blocked: 8 },
    { date: '2026-02-10', approved: 92, escalated: 15, blocked: 10 },
    { date: '2026-02-11', approved: 78, escalated: 10, blocked: 6 },
    { date: '2026-02-12', approved: 105, escalated: 18, blocked: 12 },
    { date: '2026-02-13', approved: 98, escalated: 14, blocked: 9 },
    { date: '2026-02-14', approved: 110, escalated: 20, blocked: 15 },
    { date: '2026-02-15', approved: 88, escalated: 11, blocked: 7 },
  ],
}

const stats = ref<DashboardStats>(defaultStats)
const loadingApi = ref(false)
const newCustomers = ref<any[]>([])

if (import.meta.client) {
  loadingApi.value = true
  $fetch('/api/dashboard/stats')
    .then((data: any) => {
      if (data) stats.value = data
    })
    .catch(() => {})
    .finally(() => { loadingApi.value = false })

  // Fetch customers and sort by registration date
  $fetch('/api/customers')
    .then((data: any) => {
      if (data) {
        newCustomers.value = data
          .filter((c: any) => c.registration_date)
          .sort((a: any, b: any) => new Date(b.registration_date).getTime() - new Date(a.registration_date).getTime())
          .slice(0, 6)
      }
    })
    .catch(() => {})
}

const status = computed(() => loadingApi.value ? 'pending' : 'success')

// Trend range picker
const trendRanges = [
  { label: '7D', days: 7 },
  { label: '14D', days: 14 },
  { label: '30D', days: 30 },
] as const

type TrendPoint = { date: string; approved: number; escalated: number; blocked: number }
const trendDays = ref(7)
const trendData = ref<TrendPoint[]>(defaultStats.daily_decision_trend)

function fetchTrend(days: number) {
  trendDays.value = days
  if (!import.meta.client) return
  $fetch<TrendPoint[]>(`/api/dashboard/decision-trend?days=${days}`)
    .then((data) => { if (data?.length) trendData.value = data })
    .catch(() => {})
}

// On initial load, use the trend from stats; when stats arrive, sync it
if (import.meta.client) {
  watch(() => stats.value.daily_decision_trend, (v) => {
    if (trendDays.value === 7 && v?.length) trendData.value = v
  }, { immediate: true })
}

const riskIndicatorLabels: Record<string, string> = {
  amount_anomaly: 'Amount Anomaly',
  velocity: 'Velocity',
  payment_method: 'Payment Method',
  payment_method_risk: 'Payment Method Risk',
  geographic: 'Geographic',
  geographic_signals: 'Geographic Signals',
  geographic_risk: 'Geographic Risk',
  device_fingerprint: 'Device Fingerprint',
  trading_behavior: 'Trading Behavior',
  recipient: 'Recipient Risk',
  recipient_analysis: 'Recipient Analysis',
  card_errors: 'Card Errors',
  card_error_history: 'Card Error History',
  no_trade: 'No Trade',
  rapid_funding: 'Rapid Funding',
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
    <div class="mb-3 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-gray-900">Dashboard</h1>
        <p class="text-xs text-gray-500">AI-Powered Payments Approval & Fraud Intelligence</p>
      </div>
      <CommonNotificationDropdown />
    </div>

    <template v-if="stats">
      <!-- Stats Cards -->
      <div class="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <UiCard>
          <div class="flex p-4 flex-col">
            <p class="text-sm font-medium text-gray-700">Total Payout Amount</p>
            <span class="text-3xl font-bold text-gray-900">{{ formatCurrency(stats.total_payout_amount) }}</span>
          </div>
        </UiCard>

        <UiCard>
          <div class="flex p-4 flex-col">
            <p class="text-sm font-medium text-gray-700">Auto-Approved Rate</p>
            <span class="text-3xl font-bold text-gray-900">{{ stats.auto_approved_rate }}%</span>
          </div>
        </UiCard>

        <UiCard>
          <div class="flex p-4 flex-col">
            <p class="text-sm font-medium text-gray-700">Pending Review</p>
            <span class="text-3xl font-bold text-gray-900">{{ stats.pending_review_count }}</span>
          </div>
        </UiCard>

        <UiCard>
          <div class="flex p-4 flex-col">
            <p class="text-sm font-medium text-gray-700">Active Alerts</p>
            <span class="text-3xl font-bold text-gray-900">{{ stats.active_alerts }}</span>

          </div>
        </UiCard>
      </div>

      <!-- Middle Row: Risk Distribution + Daily Trend + Processing Time -->
      <div class="mb-3 grid grid-cols-1 gap-3 lg:grid-cols-3">
        <UiCard>
          <UiCardHeader class="p-4 pb-2">
            <UiCardTitle>Risk Score Distribution</UiCardTitle>
          </UiCardHeader>
          <UiCardContent class="p-4 pt-0">
            <div class="flex items-center gap-6">
              <UiChartDonutChart
                :data="[
                  { name: 'Approved', value: stats.risk_distribution.approved },
                  { name: 'Escalated', value: stats.risk_distribution.escalated },
                  { name: 'Blocked', value: stats.risk_distribution.blocked },
                ]"
                :colors="['#22c55e', '#f59e0b', '#ef4444']"
                :width="130"
                :height="130"
                :label="String(riskDistTotal)"
                sublabel="Total"
              />
              <div class="space-y-2">
                <div class="flex items-center gap-2">
                  <span class="h-2.5 w-2.5 rounded-full bg-green-500" />
                  <span class="text-xs text-gray-600">Approved</span>
                  <span class="ml-auto text-xs font-semibold text-gray-900">{{ stats.risk_distribution.approved }}</span>
                  <span class="text-[10px] text-gray-400">({{ riskPct(stats.risk_distribution.approved) }}%)</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="h-2.5 w-2.5 rounded-full bg-amber-500" />
                  <span class="text-xs text-gray-600">Escalated</span>
                  <span class="ml-auto text-xs font-semibold text-gray-900">{{ stats.risk_distribution.escalated }}</span>
                  <span class="text-[10px] text-gray-400">({{ riskPct(stats.risk_distribution.escalated) }}%)</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="h-2.5 w-2.5 rounded-full bg-red-500" />
                  <span class="text-xs text-gray-600">Blocked</span>
                  <span class="ml-auto text-xs font-semibold text-gray-900">{{ stats.risk_distribution.blocked }}</span>
                  <span class="text-[10px] text-gray-400">({{ riskPct(stats.risk_distribution.blocked) }}%)</span>
                </div>
              </div>
            </div>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader class="flex items-center justify-between p-4 pb-2">
            <UiCardTitle>Daily Decision Trend</UiCardTitle>
            <div class="flex gap-1">
              <button
                v-for="r in trendRanges"
                :key="r.days"
                class="rounded px-2 py-0.5 text-[10px] font-medium transition-colors"
                :class="trendDays === r.days ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'"
                @click="fetchTrend(r.days)"
              >
                {{ r.label }}
              </button>
            </div>
          </UiCardHeader>
          <UiCardContent class="p-4 pt-0">
            <UiChartLineChart :data="trendData" />
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader class="p-4 pb-2">
            <UiCardTitle>Avg Decision Time</UiCardTitle>
          </UiCardHeader>
          <UiCardContent class="p-4 pt-0">
            <div class="flex flex-col items-center justify-center py-2">
              <div class="flex items-baseline gap-1">
                <span class="text-4xl font-bold text-gray-900">{{ stats.avg_decision_time_seconds.toFixed(1) }}</span>
                <span class="text-base text-gray-400">s</span>
              </div>
              <p class="mt-1 text-xs text-gray-500">Per transaction</p>
              <UiBadge variant="success" class="mt-3 gap-1.5">
                Real-time processing
              </UiBadge>
            </div>
          </UiCardContent>
        </UiCard>
      </div>

      <!-- Bottom Row: Top Risk Indicators + Recent Activity + New Customers -->
      <div class="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-3">
        <UiCard class="flex flex-col overflow-hidden">
          <UiCardHeader class="p-4 pb-2">
            <UiCardTitle>Top Risk Indicators</UiCardTitle>
          </UiCardHeader>
          <UiCardContent class="flex-1 overflow-y-auto p-4 pt-0">
            <div class="space-y-2">
              <div
                v-for="indicator in stats.top_risk_indicators"
                :key="indicator.name"
                class="flex items-center gap-3"
              >
                <span class="w-28 truncate text-xs text-gray-600">
                  {{ riskIndicatorLabels[indicator.name] || indicator.name }}
                </span>
                <div class="flex-1">
                  <ProgressRoot :model-value="(indicator.count / indicatorMaxCount()) * 100" :max="100" class="relative h-1.5 overflow-hidden bg-gray-200">
                    <ProgressIndicator
                      class="h-full transition-all"
                      style="background: linear-gradient(to right, #dc2626, #ef4444, #fca5a5)"
                      :style="{ width: `${(indicator.count / indicatorMaxCount()) * 100}%` }"
                    />
                  </ProgressRoot>
                </div>
                <span class="w-7 text-right text-xs font-semibold text-gray-700">{{ indicator.count }}</span>
              </div>
            </div>
          </UiCardContent>
        </UiCard>

        <UiCard class="flex flex-col overflow-hidden">
          <div class="flex items-center justify-between p-4 pb-2">
            <UiCardTitle>Recent Activity</UiCardTitle>
            <NuxtLink to="/withdrawals" class="text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors">
              View All
            </NuxtLink>
          </div>
          <UiCardContent class="flex-1 overflow-y-auto p-4 pt-0">
            <div class="space-y-1.5">
              <div
                v-for="activity in stats.recent_activity?.slice(0, 5)"
                :key="activity.id"
                class="flex items-center gap-2.5 rounded-lg border border-gray-100 px-2.5 py-1.5"
              >
                <div
                  class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                  :class="actionColors[activity.action] || 'text-gray-600 bg-gray-50'"
                >
                  <Icon
                    :icon="actionIcons[activity.action] || 'lucide:circle'"
                    class="h-3.5 w-3.5"
                  />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-xs font-medium text-gray-800">
                    {{ activity.customer_id }}
                  </p>
                  <p class="text-[10px] text-gray-400">{{ formatDate(activity.timestamp) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs font-semibold text-gray-900">{{ formatCurrency(activity.amount, activity.currency) }}</p>
                  <UiBadge
                    :variant="activity.action === 'blocked' ? 'destructive' : activity.action === 'escalated' ? 'warning' : 'success'"
                    class="capitalize"
                  >
                    {{ activity.action }}
                  </UiBadge>
                </div>
              </div>
            </div>
          </UiCardContent>
        </UiCard>

        <UiCard class="flex flex-col overflow-hidden">
          <div class="flex items-center justify-between p-4 pb-2">
            <UiCardTitle>New Customers</UiCardTitle>
            <NuxtLink to="/customers" class="text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors">
              View All
            </NuxtLink>
          </div>
          <UiCardContent class="flex-1 overflow-y-auto p-4 pt-0">
            <div class="space-y-1.5">
              <div
                v-for="customer in newCustomers"
                :key="customer.id"
                class="flex items-center gap-2.5 rounded-lg border border-gray-100 px-2.5 py-1.5"
              >
                <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50">
                  <Icon icon="lucide:user-plus" class="h-3.5 w-3.5 text-blue-600" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-xs font-medium text-gray-800">
                    {{ customer.name }} ({{ customer.id }})
                  </p>
                  <p class="text-[10px] text-gray-400">{{ formatDate(customer.registration_date) }}</p>
                </div>
                <!-- <div class="text-right">
                  <p class="text-xs font-semibold text-gray-900">{{ customer.country }}</p>
                  <UiBadge variant="secondary" class="capitalize">
                    New
                  </UiBadge>
                </div> -->
              </div>
            </div>
          </UiCardContent>
        </UiCard>
      </div>
    </template>

    <!-- Demo mode indicator -->
    <div v-if="status === 'error'" class="mt-2 flex items-center justify-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700">
      <Icon icon="lucide:info" class="h-4 w-4" />
      Demo mode - showing sample data. Connect backend API for live data.
    </div>
  </div>
</template>
