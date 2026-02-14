<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction, RiskIndicator } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

const props = defineProps<{
  visible: boolean
  transaction: Transaction | null
}>()

const emit = defineEmits<{
  close: []
  approve: [data: { id: string; justification: string }]
  block: [data: { id: string; justification: string }]
}>()

const justification = ref('')
const expandedIndicators = ref<Set<string>>(new Set())

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
  const map: Record<string, { bg: string; text: string; label: string }> = {
    low: { bg: 'bg-green-100', text: 'text-green-700', label: 'Low Risk' },
    medium: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Medium Risk' },
    high: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'High Risk' },
    critical: { bg: 'bg-red-100', text: 'text-red-700', label: 'Critical Risk' },
  }
  return map[level] || map.low
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

function toggleIndicator(name: string) {
  if (expandedIndicators.value.has(name)) {
    expandedIndicators.value.delete(name)
  } else {
    expandedIndicators.value.add(name)
  }
}

function handleApprove() {
  if (!props.transaction || !justification.value.trim()) return
  emit('approve', { id: props.transaction.id, justification: justification.value })
  justification.value = ''
}

function handleBlock() {
  if (!props.transaction || !justification.value.trim()) return
  emit('block', { id: props.transaction.id, justification: justification.value })
  justification.value = ''
}

function handleClose() {
  justification.value = ''
  expandedIndicators.value.clear()
  emit('close')
}

const paymentMethodIcon = computed(() => {
  if (!props.transaction) return 'lucide:credit-card'
  const map: Record<string, string> = {
    card: 'lucide:credit-card',
    ewallet: 'lucide:wallet',
    bank: 'lucide:building',
    crypto: 'lucide:bitcoin',
  }
  return map[props.transaction.payment_method] || 'lucide:credit-card'
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="visible && transaction"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50" @click="handleClose" />

        <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between p-5 border-b border-gray-200 shrink-0">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-blue-100 rounded-lg">
                <Icon icon="lucide:shield-check" class="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">Payout Review</h3>
                <p class="text-sm text-gray-500">{{ transaction.id }} - {{ transaction.withdrawal_id }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span
                class="px-3 py-1 text-xs font-medium rounded-full"
                :class="[getRiskLevelBadge(transaction.risk_level).bg, getRiskLevelBadge(transaction.risk_level).text]"
              >
                {{ getRiskLevelBadge(transaction.risk_level).label }}
              </span>
              <button class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors" @click="handleClose">
                <Icon icon="lucide:x" class="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </div>

          <!-- Scrollable Body -->
          <div class="overflow-y-auto flex-1 p-5 space-y-6">
            <!-- Top Summary Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <!-- Customer Summary -->
              <div class="bg-gray-50 rounded-lg p-4">
                <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Icon icon="lucide:user" class="w-4 h-4" />
                  Customer Summary
                </h4>
                <div class="space-y-2 text-sm">
                  <div class="flex justify-between">
                    <span class="text-gray-500">Name</span>
                    <span class="font-medium text-gray-900">{{ transaction.customer.name }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Email</span>
                    <span class="font-medium text-gray-900">{{ transaction.customer.email }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Country</span>
                    <span class="font-medium text-gray-900">{{ transaction.customer.country }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Registration</span>
                    <span class="font-medium text-gray-900">{{ formatDate(transaction.customer.registration_date) }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Account Age</span>
                    <span class="font-medium text-gray-900">{{ transaction.customer.account_age_days }} days</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Account Type</span>
                    <span class="font-medium text-gray-900">{{ transaction.customer.account_type }}</span>
                  </div>
                </div>
              </div>

              <!-- Withdrawal Details -->
              <div class="bg-gray-50 rounded-lg p-4">
                <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Icon :icon="paymentMethodIcon" class="w-4 h-4" />
                  Withdrawal Details
                </h4>
                <div class="space-y-2 text-sm">
                  <div class="flex justify-between">
                    <span class="text-gray-500">Amount</span>
                    <span class="font-semibold text-gray-900 text-base">{{ formatCurrency(transaction.amount, transaction.currency) }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Method</span>
                    <span class="font-medium text-gray-900 capitalize">{{ transaction.payment_method }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Recipient</span>
                    <span class="font-medium text-gray-900">{{ transaction.recipient.name }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Account</span>
                    <span class="font-medium text-gray-900">{{ transaction.recipient.account_number }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">IP Address</span>
                    <span class="font-medium text-gray-900">{{ transaction.ip_address }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Device</span>
                    <span class="font-medium text-gray-900">{{ transaction.device }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Composite Score -->
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Icon icon="lucide:activity" class="w-4 h-4" />
                  Composite Risk Score
                </h4>
                <span
                  class="px-3 py-1 text-sm font-bold rounded-full"
                  :class="[getRiskLevelBadge(transaction.risk_level).bg, getRiskLevelBadge(transaction.risk_level).text]"
                >
                  {{ transaction.risk_score.toFixed(2) }}
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div
                  class="h-3 rounded-full transition-all duration-500"
                  :class="getScoreBarClass(transaction.risk_score)"
                  :style="{ width: `${transaction.risk_score * 100}%` }"
                />
              </div>
              <div class="flex justify-between mt-1 text-xs text-gray-400">
                <span>0.0 (Safe)</span>
                <span>0.3</span>
                <span>0.7</span>
                <span>1.0 (Critical)</span>
              </div>
            </div>

            <!-- Risk Indicators -->
            <div>
              <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Icon icon="lucide:shield-alert" class="w-4 h-4" />
                Risk Indicator Breakdown (8 Indicators)
              </h4>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div
                  v-for="indicator in transaction.indicators"
                  :key="indicator.name"
                  class="border border-gray-200 rounded-lg overflow-hidden"
                >
                  <!-- Indicator Header -->
                  <div
                    class="p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                    @click="toggleIndicator(indicator.name)"
                  >
                    <div class="flex items-center justify-between mb-2">
                      <div class="flex items-center gap-2">
                        <Icon :icon="indicator.icon" class="w-4 h-4 text-gray-600" />
                        <span class="text-sm font-medium text-gray-800">{{ getIndicatorLabel(indicator.name) }}</span>
                      </div>
                      <div class="flex items-center gap-2">
                        <span
                          class="text-sm font-bold"
                          :class="getScoreTextClass(indicator.score)"
                        >
                          {{ indicator.score.toFixed(2) }}
                        </span>
                        <Icon
                          icon="lucide:chevron-down"
                          class="w-4 h-4 text-gray-400 transition-transform"
                          :class="expandedIndicators.has(indicator.name) ? 'rotate-180' : ''"
                        />
                      </div>
                    </div>

                    <!-- Score Bar -->
                    <div class="w-full bg-gray-200 rounded-full h-1.5 mb-2">
                      <div
                        class="h-1.5 rounded-full transition-all"
                        :class="getScoreBarClass(indicator.score)"
                        :style="{ width: `${indicator.score * 100}%` }"
                      />
                    </div>

                    <!-- Meta Row -->
                    <div class="flex items-center gap-3 text-xs text-gray-500">
                      <span class="inline-flex items-center gap-1 bg-gray-100 px-2 py-0.5 rounded-full">
                        Weight: {{ indicator.weight.toFixed(2) }}
                      </span>
                      <span class="inline-flex items-center gap-1">
                        <Icon icon="lucide:percent" class="w-3 h-3" />
                        {{ (indicator.confidence * 100).toFixed(0) }}% confidence
                      </span>
                    </div>
                  </div>

                  <!-- Expanded Details -->
                  <Transition
                    enter-active-class="transition-all duration-200 ease-out"
                    enter-from-class="max-h-0 opacity-0"
                    enter-to-class="max-h-96 opacity-100"
                    leave-active-class="transition-all duration-150 ease-in"
                    leave-from-class="max-h-96 opacity-100"
                    leave-to-class="max-h-0 opacity-0"
                  >
                    <div
                      v-if="expandedIndicators.has(indicator.name)"
                      class="border-t border-gray-100 bg-gray-50 p-3 overflow-hidden"
                    >
                      <div class="mb-2">
                        <p class="text-xs font-medium text-gray-600 mb-1">Reasoning</p>
                        <p class="text-sm text-gray-700">{{ indicator.reasoning }}</p>
                      </div>
                      <div>
                        <p class="text-xs font-medium text-gray-600 mb-1">Evidence</p>
                        <pre class="text-xs bg-gray-900 text-green-400 rounded-lg p-3 overflow-x-auto">{{ JSON.stringify(indicator.evidence, null, 2) }}</pre>
                      </div>
                    </div>
                  </Transition>
                </div>
              </div>
            </div>

            <!-- Triage Constellation Analysis -->
            <div v-if="transaction.triage" class="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
              <h4 class="text-sm font-semibold text-indigo-800 mb-3 flex items-center gap-2">
                <Icon icon="lucide:brain" class="w-4 h-4" />
                Triage Constellation Analysis
                <span class="px-2 py-0.5 bg-indigo-200 text-indigo-700 rounded-full text-xs font-medium">
                  {{ transaction.triage.elapsed_s.toFixed(1) }}s
                </span>
              </h4>
              <p class="text-sm text-indigo-900 leading-relaxed mb-3">{{ transaction.triage.constellation_analysis }}</p>
              <div v-if="transaction.triage.assignments.length" class="flex flex-wrap gap-2">
                <span
                  v-for="a in transaction.triage.assignments"
                  :key="a.investigator"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                  :class="a.priority === 'high' ? 'bg-red-100 text-red-700' : a.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'"
                >
                  <Icon icon="lucide:search" class="w-3 h-3" />
                  {{ a.investigator.replace('_', ' ') }}
                  <span class="opacity-70">({{ a.priority }})</span>
                </span>
              </div>
            </div>

            <!-- Investigator Findings -->
            <div v-if="transaction.investigators?.length">
              <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Icon icon="lucide:search" class="w-4 h-4" />
                Investigator Findings ({{ transaction.investigators.length }})
              </h4>
              <div class="grid grid-cols-1 gap-3">
                <div
                  v-for="inv in transaction.investigators"
                  :key="inv.investigator_name"
                  class="border rounded-lg p-4"
                  :class="inv.score >= 0.7 ? 'border-red-200 bg-red-50/50' : inv.score >= 0.3 ? 'border-yellow-200 bg-yellow-50/50' : 'border-green-200 bg-green-50/50'"
                >
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-semibold text-gray-800">{{ inv.display_name }}</span>
                    <div class="flex items-center gap-3">
                      <span class="text-xs text-gray-400">{{ inv.elapsed_s.toFixed(1) }}s</span>
                      <span
                        class="text-sm font-bold"
                        :class="getScoreTextClass(inv.score)"
                      >
                        {{ inv.score.toFixed(2) }}
                      </span>
                    </div>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-1.5 mb-2">
                    <div
                      class="h-1.5 rounded-full transition-all"
                      :class="getScoreBarClass(inv.score)"
                      :style="{ width: `${inv.score * 100}%` }"
                    />
                  </div>
                  <div class="flex items-center gap-2 mb-2">
                    <span class="text-xs text-gray-500">
                      <Icon icon="lucide:percent" class="w-3 h-3 inline" />
                      {{ (inv.confidence * 100).toFixed(0) }}% confidence
                    </span>
                  </div>
                  <p class="text-sm text-gray-700 leading-relaxed">{{ inv.reasoning }}</p>
                </div>
              </div>
            </div>

            <!-- Officer Override Info (for auto-approved) -->
            <div v-if="transaction.status === 'approved'" class="bg-blue-50 rounded-lg p-3 border border-blue-200">
              <div class="flex items-center gap-2 text-blue-700">
                <Icon icon="lucide:info" class="w-4 h-4 shrink-0" />
                <span class="text-sm">Auto-approved by AI system. You can override this decision if needed.</span>
              </div>
            </div>

            <!-- Justification (always shown) -->
            <div class="bg-gray-50 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Icon icon="lucide:message-square" class="w-4 h-4" />
                {{ transaction.status === 'approved' ? 'Override Justification' : 'Decision Justification' }}
                <span class="text-red-500">*</span>
              </h4>
              <textarea
                v-model="justification"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                :placeholder="transaction.status === 'approved' ? 'Provide reason for revoking approval (required)...' : 'Provide your reasoning for the decision (required)...'"
              />
            </div>
          </div>

          <!-- Footer Actions -->
          <div class="flex items-center justify-between p-5 border-t border-gray-200 shrink-0 bg-white rounded-b-xl">
            <button
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              @click="handleClose"
            >
              Cancel
            </button>
            <div class="flex items-center gap-3">
              <button
                class="px-5 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                :disabled="!justification.trim()"
                @click="handleBlock"
              >
                <Icon icon="lucide:ban" class="w-4 h-4" />
                {{ transaction.status === 'approved' ? 'Revoke & Block' : 'Block' }}
              </button>
              <button
                v-if="transaction.status !== 'approved'"
                class="px-5 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                :disabled="!justification.trim()"
                @click="handleApprove"
              >
                <Icon icon="lucide:check-circle" class="w-4 h-4" />
                Approve
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
