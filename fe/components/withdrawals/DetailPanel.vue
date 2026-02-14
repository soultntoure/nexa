<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

const props = defineProps<{
  transaction: Transaction
}>()

interface LinkedAccount {
  customer_id: string
  customer_name: string
  is_locked?: boolean
}

const emit = defineEmits<{
  close: []
  approve: [justification: string]
  block: [justification: string, lockConnected: boolean]
  flag: []
  discuss: []
  'customer-profile': []
}>()

const activeTab = ref<'overview' | 'risk' | 'about'>('overview')
const justification = ref('')
const expandedIndicators = ref<string[]>([])
const showScoringFactors = ref(false)
const blockMode = ref(false)
const loadingLinked = ref(false)
const linkedAccounts = ref<LinkedAccount[]>([])
const lockConnected = ref(true)

watch(() => props.transaction.id, () => {
  activeTab.value = 'overview'
  justification.value = ''
  expandedIndicators.value = []
  blockMode.value = false
  linkedAccounts.value = []
})

const paymentMethodIcons: Record<string, string> = {
  card: 'lucide:credit-card',
  ewallet: 'lucide:wallet',
  bank: 'lucide:building',
  crypto: 'lucide:bitcoin',
}

function getScoreBarClass(score: number): string {
  if (score >= 0.7) return 'bg-red-500'
  if (score >= 0.3) return 'bg-yellow-500'
  return 'bg-green-500'
}

function getScoreTextClass(score: number): string {
  if (score >= 0.7) return 'text-red-600'
  if (score >= 0.3) return 'text-yellow-600'
  return 'text-green-600'
}

function getRiskLevelBadge(level: string) {
  const map = {
    low: { bg: 'bg-green-100', text: 'text-green-700', label: 'Low Risk' },
    medium: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Medium Risk' },
    high: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'High Risk' },
    critical: { bg: 'bg-red-100', text: 'text-red-700', label: 'Critical Risk' },
  } as const
  const normalized = level.toLowerCase() as keyof typeof map
  return map[normalized] ?? map.low
}

function getIndicatorLabel(name: string): string {
  const labels: Record<string, string> = {
    amount_anomaly: 'Amount Anomaly',
    velocity: 'Transaction Velocity',
    payment_method: 'Payment Method',
    geographic: 'Geographic Analysis',
    device_fingerprint: 'Device Fingerprint',
    trading_behavior: 'Trading Behavior',
    recipient: 'Recipient Analysis',
    card_errors: 'Card Error History',
  }
  return labels[name] || name
}

const statusBadgeClasses: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  approved: 'bg-green-100 text-green-700',
  escalated: 'bg-yellow-100 text-yellow-700',
  blocked: 'bg-red-100 text-red-700',
}

function handleApprove() {
  if (!justification.value.trim()) {
    activeTab.value = 'about'
    blockMode.value = false
    return
  }
  emit('approve', justification.value)
  justification.value = ''
}

const hasConnected = computed(() => linkedAccounts.value.length > 0)

async function handleBlock() {
  activeTab.value = 'about'
  blockMode.value = true
  loadingLinked.value = true
  linkedAccounts.value = []
  lockConnected.value = true
  try {
    const result = await $fetch<{ shared: boolean; linked_count: number; linked_accounts?: LinkedAccount[] }>(
      `/api/alerts/card-check/${props.transaction.customer.external_id}`,
    )
    linkedAccounts.value = (result.linked_accounts ?? []).filter(a => a.customer_id !== props.transaction.customer.external_id)
  } catch {
    linkedAccounts.value = []
  } finally {
    loadingLinked.value = false
  }
}

function confirmBlock() {
  if (!justification.value.trim()) return
  emit('block', justification.value.trim(), hasConnected.value && lockConnected.value)
  justification.value = ''
  blockMode.value = false
}

function cancelBlock() {
  blockMode.value = false
}

const withdrawalRatio = computed(() => {
  if (props.transaction.customer.total_deposits <= 0) return 0
  return props.transaction.customer.total_withdrawals / props.transaction.customer.total_deposits
})

const ratioColor = computed(() => {
  if (withdrawalRatio.value > 0.8) return 'text-red-600'
  if (withdrawalRatio.value > 0.5) return 'text-yellow-600'
  return 'text-green-600'
})

const ratioBarColor = computed(() => {
  if (withdrawalRatio.value > 0.8) return 'bg-red-500'
  if (withdrawalRatio.value > 0.5) return 'bg-yellow-500'
  return 'bg-green-500'
})
</script>

<template>
  <div class="relative flex flex-col h-full bg-white">
    <!-- Close Button -->
    <div class="absolute top-3 right-3 z-10">
      <button
        class="p-1.5 bg-white/90 hover:bg-gray-100 rounded-full shadow-sm transition-colors"
        @click="emit('close')"
      >
        <Icon icon="lucide:x" class="w-5 h-5 text-gray-500" />
      </button>
    </div>

    <!-- Header -->
    <div class="shrink-0 px-5 pt-5 pb-4 border-b border-gray-200">
      <!-- Customer Info -->
      <div class="flex items-start gap-3 mb-3 pr-8">
        <div class="w-12 h-12 bg-primary-50 rounded-full flex items-center justify-center shrink-0">
          <span class="text-primary-700 font-bold text-sm">
            {{ transaction.customer.name.split(' ').map((n: string) => n[0]).join('') }}
          </span>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-0.5">
            <h2 class="text-lg font-bold text-gray-900 truncate">{{ transaction.customer.name }}</h2>
            <span
              class="inline-flex px-2 py-0.5 text-xs font-medium rounded-full capitalize shrink-0"
              :class="statusBadgeClasses[transaction.status]"
            >
              {{ transaction.status }}
            </span>
          </div>
          <div class="flex items-center gap-2 mb-1">
            <span
              class="text-sm font-bold"
              :class="getScoreTextClass(transaction.risk_score)"
            >
              {{ transaction.risk_score.toFixed(2) }}
            </span>
            <div class="flex-1 max-w-[120px] bg-gray-200 rounded-full h-1.5">
              <div
                class="h-1.5 rounded-full transition-all"
                :class="getScoreBarClass(transaction.risk_score)"
                :style="{ width: `${transaction.risk_score * 100}%` }"
              />
            </div>
            <span
              class="text-xs font-medium px-2 py-0.5 rounded-full"
              :class="[getRiskLevelBadge(transaction.risk_level).bg, getRiskLevelBadge(transaction.risk_level).text]"
            >
              {{ getRiskLevelBadge(transaction.risk_level).label }}
            </span>
          </div>
          <p class="text-sm text-gray-500">{{ transaction.customer.email }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <TabsRoot v-model="activeTab" class="-mb-4 -mx-5 px-5">
        <TabsList class="flex items-center gap-0 border-b border-gray-200">
          <TabsTrigger
            v-for="tab in ([
              { key: 'overview', label: 'Overview' },
              { key: 'risk', label: 'Risk Analysis' },
              { key: 'about', label: 'About' },
            ] as const)"
            :key="tab.key"
            :value="tab.key"
            class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors border-transparent text-gray-500 hover:text-gray-700 data-[state=active]:border-primary-500 data-[state=active]:text-primary-600"
          >
            {{ tab.label }}
          </TabsTrigger>
        </TabsList>
      </TabsRoot>
    </div>

    <!-- Action Buttons (Google Maps style) -->
    <div class="shrink-0 flex justify-around py-3 px-4 border-b border-gray-200 bg-gray-50/50">
      <button
        class="flex flex-col items-center gap-1"
        @click="handleApprove"
        :title="justification.trim() ? 'Approve withdrawal' : 'Write justification first'"
      >
        <div class="w-10 h-10 rounded-full bg-green-50 border border-green-200 flex items-center justify-center hover:bg-green-100 transition-colors">
          <Icon icon="lucide:check" class="w-5 h-5 text-green-600" />
        </div>
        <span class="text-xs font-medium text-green-700">Approve</span>
      </button>
      <button class="flex flex-col items-center gap-1" @click="emit('flag')">
        <div class="w-10 h-10 rounded-full bg-orange-50 border border-orange-200 flex items-center justify-center hover:bg-orange-100 transition-colors">
          <Icon icon="lucide:flag" class="w-5 h-5 text-orange-500" />
        </div>
        <span class="text-xs font-medium text-orange-600">Flag</span>
      </button>
      <button
        class="flex flex-col items-center gap-1"
        @click="handleBlock"
        title="Block withdrawal"
      >
        <div class="w-10 h-10 rounded-full bg-red-50 border border-red-200 flex items-center justify-center hover:bg-red-100 transition-colors">
          <Icon icon="lucide:ban" class="w-5 h-5 text-red-500" />
        </div>
        <span class="text-xs font-medium text-red-600">Block</span>
      </button>
      <button class="flex flex-col items-center gap-1" @click="emit('discuss')">
        <div class="w-10 h-10 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center hover:bg-indigo-100 transition-colors">
          <Icon icon="lucide:message-square" class="w-5 h-5 text-indigo-500" />
        </div>
        <span class="text-xs font-medium text-indigo-600">Discuss</span>
      </button>
      <button class="flex flex-col items-center gap-1" @click="emit('customer-profile')">
        <div class="w-10 h-10 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center hover:bg-blue-100 transition-colors">
          <Icon icon="lucide:user" class="w-5 h-5 text-blue-500" />
        </div>
        <span class="text-xs font-medium text-blue-600">Profile</span>
      </button>
    </div>

    <!-- Scrollable Tab Content -->
    <div class="flex-1 overflow-y-auto">
      <!-- OVERVIEW TAB -->
      <div v-if="activeTab === 'overview'" class="p-5 space-y-4">
        <!-- Transaction Details (Google Maps info rows style) -->
        <div class="space-y-0 divide-y divide-gray-100">
          <div class="flex items-center gap-3 py-3">
            <Icon icon="lucide:banknote" class="w-5 h-5 text-gray-400 shrink-0" />
            <div>
              <p class="text-sm font-semibold text-gray-900">{{ formatCurrency(transaction.amount, transaction.currency) }}</p>
              <p class="text-xs text-gray-500">Withdrawal Amount</p>
            </div>
          </div>
          <div class="flex items-center gap-3 py-3">
            <Icon :icon="paymentMethodIcons[transaction.payment_method] || 'lucide:credit-card'" class="w-5 h-5 text-gray-400 shrink-0" />
            <div>
              <p class="text-sm text-gray-900 capitalize">{{ transaction.payment_method }}</p>
              <p class="text-xs text-gray-500">Payment Method</p>
            </div>
          </div>
          <div class="flex items-center gap-3 py-3">
            <Icon icon="lucide:user-check" class="w-5 h-5 text-gray-400 shrink-0" />
            <div>
              <p class="text-sm text-gray-900">{{ transaction.recipient.name }}</p>
              <p class="text-xs text-gray-500">{{ transaction.recipient.account_number }} &middot; {{ transaction.recipient.bank }}</p>
            </div>
          </div>
          <div class="flex items-center gap-3 py-3">
            <Icon icon="lucide:globe" class="w-5 h-5 text-gray-400 shrink-0" />
            <div>
              <p class="text-sm text-gray-900">{{ transaction.ip_address }}</p>
              <p class="text-xs text-gray-500">IP Address</p>
            </div>
          </div>
          <div class="flex items-center gap-3 py-3">
            <Icon icon="lucide:monitor-smartphone" class="w-5 h-5 text-gray-400 shrink-0" />
            <div>
              <p class="text-sm text-gray-900">{{ transaction.device }}</p>
              <p class="text-xs text-gray-500">Device</p>
            </div>
          </div>
          <div class="flex items-center gap-3 py-3">
            <Icon icon="lucide:clock" class="w-5 h-5 text-gray-400 shrink-0" />
            <div>
              <p class="text-sm text-gray-900">{{ formatDate(transaction.created_at) }}</p>
              <p class="text-xs text-gray-500">Requested</p>
            </div>
          </div>
        </div>

        <!-- Customer Summary Card -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Customer</h4>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <p class="text-xs text-gray-500">Country</p>
              <p class="text-sm font-medium text-gray-900">{{ transaction.customer.country }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Account Type</p>
              <p class="text-sm font-medium text-gray-900 capitalize">{{ transaction.customer.account_type }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Account Age</p>
              <p class="text-sm font-medium text-gray-900">{{ transaction.customer.account_age_days }} days</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Registered</p>
              <p class="text-sm font-medium text-gray-900">{{ formatDate(transaction.customer.registration_date, 'MMM dd, yyyy') }}</p>
            </div>
          </div>
        </div>

        <!-- Financial Summary -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Financial</h4>
          <div class="grid grid-cols-2 gap-3 mb-3">
            <div class="p-2.5 bg-green-50 rounded-lg border border-green-100">
              <div class="flex items-center gap-1.5 mb-1">
                <Icon icon="lucide:arrow-down-circle" class="w-3.5 h-3.5 text-green-600" />
                <p class="text-xs text-green-700 uppercase">Deposits</p>
              </div>
              <p class="text-sm font-bold text-green-800">{{ formatCurrency(transaction.customer.total_deposits) }}</p>
            </div>
            <div class="p-2.5 bg-red-50 rounded-lg border border-red-100">
              <div class="flex items-center gap-1.5 mb-1">
                <Icon icon="lucide:arrow-up-circle" class="w-3.5 h-3.5 text-red-600" />
                <p class="text-xs text-red-700 uppercase">Withdrawals</p>
              </div>
              <p class="text-sm font-bold text-red-800">{{ formatCurrency(transaction.customer.total_withdrawals) }}</p>
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs text-gray-500">Withdrawal Ratio</span>
              <span class="text-xs font-bold" :class="ratioColor">
                {{ (withdrawalRatio * 100).toFixed(1) }}%
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-1.5">
              <div
                class="h-1.5 rounded-full transition-all"
                :class="ratioBarColor"
                :style="{ width: `${Math.min(withdrawalRatio * 100, 100)}%` }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- RISK ANALYSIS TAB -->
      <div v-if="activeTab === 'risk'" class="p-5 space-y-5">
        <!-- Composite Risk Score -->
        <div class="bg-gray-50 rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
              <Icon icon="lucide:activity" class="w-4 h-4" />
              Composite Score
            </h4>
            <div class="flex items-center gap-2">
              <!-- <button
                class="px-2.5 py-1 text-[10px] font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
                @click="showScoringFactors = true"
              >
                Scoring factors
              </button> -->
              <span
                class="px-2.5 py-1 text-sm font-bold rounded-full"
                :class="[getRiskLevelBadge(transaction.risk_level).bg, getRiskLevelBadge(transaction.risk_level).text]"
              >
                {{ transaction.risk_score.toFixed(2) }}
              </span>
            </div>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2.5">
            <div
              class="h-2.5 rounded-full transition-all duration-500"
              :class="getScoreBarClass(transaction.risk_score)"
              :style="{ width: `${transaction.risk_score * 100}%` }"
            />
          </div>
          <div class="flex justify-between mt-1 text-xs text-gray-400">
            <span>0.0 Safe</span>
            <span>0.3</span>
            <span>0.7</span>
            <span>1.0 Critical</span>
          </div>
        </div>

        <!-- Risk Indicators -->
        <div>
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Icon icon="lucide:shield-alert" class="w-4 h-4" />
            Risk Indicators ({{ transaction.indicators.length }})
          </h4>
          <AccordionRoot v-model="expandedIndicators" type="multiple" class="space-y-2">
            <AccordionItem
              v-for="indicator in transaction.indicators"
              :key="indicator.name"
              :value="indicator.name"
              class="border border-gray-200 rounded-lg overflow-hidden"
            >
              <AccordionHeader>
                <AccordionTrigger class="w-full p-3 cursor-pointer hover:bg-gray-50 transition-colors text-left">
                  <div class="flex items-center justify-between mb-1.5">
                    <div class="flex items-center gap-2">
                      <Icon :icon="indicator.icon" class="w-4 h-4 text-gray-500" />
                      <span class="text-sm font-medium text-gray-800">{{ getIndicatorLabel(indicator.name) }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-bold" :class="getScoreTextClass(indicator.score)">
                        {{ indicator.score.toFixed(2) }}
                      </span>
                      <Icon
                        icon="lucide:chevron-down"
                        class="w-4 h-4 text-gray-400 transition-transform data-[state=open]:rotate-180"
                      />
                    </div>
                  </div>
                  <ProgressRoot :model-value="indicator.score * 100" :max="100" class="w-full bg-gray-200 rounded-full h-1 overflow-hidden">
                    <ProgressIndicator
                      class="h-1 rounded-full transition-all"
                      :class="getScoreBarClass(indicator.score)"
                      :style="{ width: `${indicator.score * 100}%` }"
                    />
                  </ProgressRoot>
                  <div class="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                    <span class="bg-gray-100 px-1.5 py-0.5 rounded-full">W: {{ indicator.weight.toFixed(2) }}</span>
                    <span>{{ (indicator.confidence * 100).toFixed(0) }}% conf</span>
                  </div>
                </AccordionTrigger>
              </AccordionHeader>

              <!-- Expanded Detail -->
              <AccordionContent class="border-t border-gray-100 bg-gray-50 p-3">
                <p class="text-xs font-medium text-gray-600 mb-1">Reasoning</p>
                <p class="text-sm text-gray-700 mb-2">{{ indicator.reasoning }}</p>
                <p class="text-xs font-medium text-gray-600 mb-1">Evidence</p>
                <pre class="text-xs bg-gray-900 text-green-400 rounded-lg p-2.5 overflow-x-auto">{{ JSON.stringify(indicator.evidence, null, 2) }}</pre>
              </AccordionContent>
            </AccordionItem>
          </AccordionRoot>
        </div>

        <!-- AI Verdict -->
        <div v-if="transaction.triage" class="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-xs font-semibold text-indigo-800 uppercase tracking-wider flex items-center gap-1.5">
              <Icon icon="lucide:brain" class="w-4 h-4" />
              AI Verdict
              <span class="px-1.5 py-0.5 bg-indigo-200 text-indigo-700 rounded-full text-xs font-medium">
                {{ transaction.triage.elapsed_s.toFixed(1) }}s
              </span>
            </h4>
            <div v-if="transaction.triage.decision" class="flex items-center gap-2">
              <span
                class="px-2 py-0.5 rounded-full text-xs font-bold uppercase"
                :class="transaction.triage.decision === 'blocked' ? 'bg-red-100 text-red-700' : transaction.triage.decision === 'escalated' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'"
              >
                {{ transaction.triage.decision }}
              </span>
              <span v-if="transaction.triage.confidence" class="text-xs text-indigo-600">
                {{ (transaction.triage.confidence * 100).toFixed(0) }}%
              </span>
            </div>
          </div>
          <p v-if="transaction.triage.decision_reasoning" class="text-sm text-indigo-900 leading-relaxed mb-2">
            {{ transaction.triage.decision_reasoning }}
          </p>
          <p class="text-sm text-indigo-700 leading-relaxed mb-2">{{ transaction.triage.constellation_analysis }}</p>
          <div v-if="transaction.triage.assignments.length" class="flex flex-wrap gap-1.5">
            <span
              v-for="a in transaction.triage.assignments"
              :key="a.investigator"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700"
            >
              <Icon icon="lucide:search" class="w-3 h-3" />
              {{ a.investigator.replace('_', ' ') }}
            </span>
          </div>
        </div>

        <!-- Investigator Findings -->
        <div v-if="transaction.investigators?.length">
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Icon icon="lucide:search" class="w-4 h-4" />
            Investigators ({{ transaction.investigators.length }})
          </h4>
          <div class="space-y-2">
            <div
              v-for="inv in transaction.investigators"
              :key="inv.investigator_name"
              class="border rounded-lg p-3"
              :class="inv.score >= 0.7 ? 'border-red-200 bg-red-50/50' : inv.score >= 0.3 ? 'border-yellow-200 bg-yellow-50/50' : 'border-green-200 bg-green-50/50'"
            >
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-sm font-semibold text-gray-800">{{ inv.display_name }}</span>
                <div class="flex items-center gap-2">
                  <span class="text-xs text-gray-400">{{ inv.elapsed_s.toFixed(1) }}s</span>
                  <span class="text-sm font-bold" :class="getScoreTextClass(inv.score)">
                    {{ inv.score.toFixed(2) }}
                  </span>
                </div>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-1 mb-1.5">
                <div
                  class="h-1 rounded-full"
                  :class="getScoreBarClass(inv.score)"
                  :style="{ width: `${inv.score * 100}%` }"
                />
              </div>
              <p class="text-xs text-gray-500 mb-1">
                {{ (inv.confidence * 100).toFixed(0) }}% confidence
              </p>
              <p class="text-sm text-gray-700 leading-relaxed">{{ inv.reasoning }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ABOUT TAB -->
      <div v-if="activeTab === 'about'" class="p-5 space-y-4">
        <!-- Transaction IDs -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Transaction IDs</h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-500">Transaction</span>
              <span class="font-mono text-xs text-gray-700">{{ transaction.id }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">Withdrawal</span>
              <span class="font-mono text-xs text-gray-700">{{ transaction.withdrawal_id }}</span>
            </div>
            <div v-if="transaction.evaluation_id" class="flex justify-between">
              <span class="text-gray-500">Evaluation</span>
              <span class="font-mono text-xs text-gray-700">{{ transaction.evaluation_id }}</span>
            </div>
          </div>
        </div>

        <!-- Auto-approved Info -->
        <div v-if="transaction.status === 'approved'" class="bg-blue-50 rounded-lg p-3 border border-blue-200">
          <div class="flex items-center gap-2 text-blue-700">
            <Icon icon="lucide:info" class="w-4 h-4 shrink-0" />
            <span class="text-sm">Auto-approved by AI system. You can override this decision.</span>
          </div>
        </div>

        <!-- Decision Area -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            {{ blockMode ? 'Block Withdrawal' : transaction.status === 'approved' ? 'Override Decision' : 'Make Decision' }}
          </h4>

          <!-- Justification textarea -->
          <textarea
            v-model="justification"
            rows="3"
            class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 resize-none"
            :class="blockMode
              ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
              : 'border-gray-300 focus:ring-primary-500 focus:border-primary-500'"
            :placeholder="blockMode
              ? 'Provide your reasoning for blocking this withdrawal (required)...'
              : transaction.status === 'approved'
                ? 'Provide reason for revoking approval (required)...'
                : 'Provide your reasoning (required)...'"
          />

          <!-- Block mode: connected accounts inline -->
          <div v-if="blockMode" class="mt-3 space-y-3">
            <!-- Loading state -->
            <div v-if="loadingLinked" class="flex items-center justify-center py-3">
              <Icon icon="lucide:loader-2" class="w-4 h-4 text-gray-400 animate-spin" />
              <span class="ml-2 text-sm text-gray-500">Checking connected accounts...</span>
            </div>

            <!-- Connected accounts found -->
            <template v-else-if="hasConnected">
              <div class="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5">
                <Icon icon="lucide:alert-triangle" class="w-4 h-4 text-amber-600 shrink-0" />
                <p class="text-xs text-amber-800">
                  <strong>{{ linkedAccounts.length }}</strong> connected account{{ linkedAccounts.length > 1 ? 's' : '' }} detected sharing payment methods.
                </p>
              </div>

              <div class="rounded-lg border border-gray-200 divide-y divide-gray-100">
                <div
                  v-for="account in linkedAccounts"
                  :key="account.customer_id"
                  class="flex items-center justify-between px-3 py-2"
                >
                  <div class="flex items-center gap-2">
                    <Icon icon="lucide:user" class="w-3.5 h-3.5 text-gray-400" />
                    <div>
                      <p class="text-xs font-medium text-gray-800">{{ account.customer_name }}</p>
                      <p class="text-xs text-gray-500 font-mono">{{ account.customer_id }}</p>
                    </div>
                  </div>
                  <span
                    v-if="account.is_locked"
                    class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700"
                  >
                    <Icon icon="lucide:lock" class="w-2.5 h-2.5" />
                    Locked
                  </span>
                </div>
              </div>

              <label class="flex items-start gap-2.5 cursor-pointer rounded-lg border border-gray-200 p-2.5 hover:bg-gray-50 transition-colors">
                <input
                  v-model="lockConnected"
                  type="checkbox"
                  class="mt-0.5 rounded text-red-600 focus:ring-red-500"
                />
                <div>
                  <p class="text-xs font-medium text-gray-800">Lock all connected accounts</p>
                  <p class="text-xs text-gray-500">Block withdrawals on all {{ linkedAccounts.length }} linked account{{ linkedAccounts.length > 1 ? 's' : '' }}.</p>
                </div>
              </label>
            </template>

            <!-- No connected accounts -->
            <div v-else class="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-2.5">
              <Icon icon="lucide:check-circle" class="w-4 h-4 text-green-500 shrink-0" />
              <p class="text-xs text-gray-600">No connected accounts found. Only this withdrawal will be blocked.</p>
            </div>

            <!-- Block mode buttons -->
            <div class="flex items-center gap-2">
              <button
                class="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                @click="cancelBlock"
              >
                Cancel
              </button>
              <button
                class="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                :disabled="!justification.trim() || loadingLinked"
                @click="confirmBlock"
              >
                <Icon icon="lucide:ban" class="w-4 h-4" />
                {{ hasConnected && lockConnected ? `Block + Lock ${linkedAccounts.length}` : 'Block' }}
              </button>
            </div>
          </div>

          <!-- Normal mode buttons -->
          <div v-else class="flex items-center gap-2 mt-3">
            <button
              class="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
              @click="handleBlock"
            >
              <Icon icon="lucide:ban" class="w-4 h-4" />
              {{ transaction.status === 'approved' ? 'Revoke & Block' : 'Block' }}
            </button>
            <button
              v-if="transaction.status !== 'approved'"
              class="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              :disabled="!justification.trim()"
              @click="handleApprove"
            >
              <Icon icon="lucide:check-circle" class="w-4 h-4" />
              Approve
            </button>
          </div>
        </div>

        <!-- Timestamps -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Timeline</h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-500">Created</span>
              <span class="text-gray-900">{{ formatDate(transaction.created_at) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">Updated</span>
              <span class="text-gray-900">{{ formatDate(transaction.updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <ScoringFactorsDrawer
    :visible="showScoringFactors"
    :customer-id="transaction.customer.external_id"
    :risk-score="transaction.risk_score"
    :decision="transaction.status"
    @close="showScoringFactors = false"
  />
</template>
