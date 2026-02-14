<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction, TransactionStatus } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

useHead({ title: 'Withdrawals - Nexa' })

const {
  selectedStatus,
  searchQuery,
  currentPage,
  dateFrom,
  dateTo,
  filteredTransactions,
  paginatedTransactions,
  totalPages,
  statusCounts,
  updateTransactionStatus,
} = useTransactions()

const showPayoutReview = ref(false)
const showFlagModal = ref(false)
const showCustomerSummary = ref(false)
const selectedTransaction = ref<Transaction | null>(null)

const statusTabs: { key: TransactionStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'blocked', label: 'Blocked' },
]

const paymentMethodIcons: Record<string, string> = {
  card: 'lucide:credit-card',
  ewallet: 'lucide:wallet',
  bank: 'lucide:building',
  crypto: 'lucide:bitcoin',
}

const statusBadgeClasses: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  approved: 'bg-green-100 text-green-700',
  escalated: 'bg-yellow-100 text-yellow-700',
  blocked: 'bg-red-100 text-red-700',
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

function openPayoutReview(tx: Transaction) {
  selectedTransaction.value = tx
  showPayoutReview.value = true
}

function openFlagModal(tx: Transaction) {
  selectedTransaction.value = tx
  showFlagModal.value = true
}

function openCustomerSummary(tx: Transaction) {
  selectedTransaction.value = tx
  showCustomerSummary.value = true
}

async function submitDecisionToBE(tx: Transaction, action: 'approved' | 'blocked', reason: string) {
  try {
    await $fetch('/api/payout/decision', {
      method: 'POST',
      body: {
        withdrawal_id: tx.withdrawal_id || crypto.randomUUID(),
        evaluation_id: crypto.randomUUID(),
        officer_id: 'officer-demo-001',
        action,
        reason,
      },
    })
  } catch {
    // BE call failed — local state update still proceeds
  }
}

async function handleApprove(data: { id: string; justification: string }) {
  const tx = filteredTransactions.value.find(t => t.id === data.id)
  if (tx) await submitDecisionToBE(tx, 'approved', data.justification)
  updateTransactionStatus(data.id, 'approved')
  showPayoutReview.value = false
  selectedTransaction.value = null
}

async function handleBlock(data: { id: string; justification: string }) {
  const tx = filteredTransactions.value.find(t => t.id === data.id)
  if (tx) await submitDecisionToBE(tx, 'blocked', data.justification)
  updateTransactionStatus(data.id, 'blocked')
  showPayoutReview.value = false
  selectedTransaction.value = null
}

async function handleQuickApprove(tx: Transaction) {
  await submitDecisionToBE(tx, 'approved', 'Quick approval by officer')
  updateTransactionStatus(tx.id, 'approved')
}

function handleFlag(data: { reason: string; notes: string }) {
  if (selectedTransaction.value) {
    updateTransactionStatus(selectedTransaction.value.id, 'escalated')
  }
  showFlagModal.value = false
  selectedTransaction.value = null
}

async function handleQuickBlock(tx: Transaction) {
  await submitDecisionToBE(tx, 'blocked', 'Quick block by officer')
  updateTransactionStatus(tx.id, 'blocked')
}

function getRowActions(tx: Transaction) {
  const actions = [
    { label: 'View Details', icon: 'lucide:eye', handler: () => openPayoutReview(tx) },
    { label: 'Customer Profile', icon: 'lucide:user', handler: () => openCustomerSummary(tx) },
  ]
  if (tx.status === 'approved') {
    actions.push(
      { label: 'Revoke Approval', icon: 'lucide:shield-off', color: 'red', handler: () => openPayoutReview(tx) },
    )
  } else {
    actions.push(
      { label: 'Approve', icon: 'lucide:check-circle', color: 'green', handler: () => handleQuickApprove(tx) },
      { label: 'Flag Account', icon: 'lucide:flag', color: 'orange', handler: () => openFlagModal(tx) },
      { label: 'Block Account', icon: 'lucide:ban', color: 'red', handler: () => handleQuickBlock(tx) },
    )
  }
  return actions
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Withdrawal Review Queue</h1>
        <p class="text-sm text-gray-500 mt-1">Review and approve withdrawal requests with AI-powered risk analysis</p>
      </div>
    </div>

    <!-- Status Filter Tabs -->
    <div class="flex items-center gap-1 bg-gray-100 p-1 rounded-lg w-fit">
      <button
        v-for="tab in statusTabs"
        :key="tab.key"
        class="px-4 py-2 text-sm font-medium rounded-md transition-all"
        :class="selectedStatus === tab.key
          ? 'bg-white text-gray-900 shadow-sm'
          : 'text-gray-600 hover:text-gray-800'"
        @click="selectedStatus = tab.key; currentPage = 1"
      >
        {{ tab.label }}
        <span
          class="ml-1.5 px-1.5 py-0.5 text-xs rounded-full"
          :class="selectedStatus === tab.key ? 'bg-gray-200 text-gray-700' : 'bg-gray-200/70 text-gray-500'"
        >
          {{ statusCounts[tab.key] }}
        </span>
      </button>
    </div>

    <!-- Search & Date Filter -->
    <div class="flex flex-wrap items-center gap-4">
      <div class="relative flex-1 min-w-[280px] max-w-md">
        <Icon icon="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name, email, or transaction ID..."
          class="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          @input="currentPage = 1"
        >
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="dateFrom"
          type="date"
          class="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
        <span class="text-gray-400 text-sm">to</span>
        <input
          v-model="dateTo"
          type="date"
          class="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
      </div>
    </div>

    <!-- Transactions Table -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="bg-gray-50 border-b border-gray-200">
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Customer</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Amount</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Method</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Risk Score</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
              <th class="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="tx in paginatedTransactions"
              :key="tx.id"
              class="hover:bg-gray-50/50 transition-colors cursor-pointer"
              @click="openPayoutReview(tx)"
            >
              <!-- Customer -->
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 bg-primary-50 rounded-full flex items-center justify-center shrink-0">
                    <span class="text-primary-700 font-medium text-xs">
                      {{ tx.customer.name.split(' ').map(n => n[0]).join('') }}
                    </span>
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">{{ tx.customer.name }}</p>
                    <p class="text-xs text-gray-500 truncate">{{ tx.customer.email }}</p>
                  </div>
                </div>
              </td>

              <!-- Amount -->
              <td class="px-4 py-3.5">
                <span class="text-sm font-semibold text-gray-900">{{ formatCurrency(tx.amount, tx.currency) }}</span>
              </td>

              <!-- Payment Method -->
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-2">
                  <Icon :icon="paymentMethodIcons[tx.payment_method]" class="w-4 h-4 text-gray-500" />
                  <span class="text-sm text-gray-600 capitalize">{{ tx.payment_method }}</span>
                </div>
              </td>

              <!-- Risk Score -->
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-2.5 min-w-[130px]">
                  <div class="flex-1 bg-gray-200 rounded-full h-1.5">
                    <div
                      class="h-1.5 rounded-full transition-all"
                      :class="getScoreBarClass(tx.risk_score)"
                      :style="{ width: `${tx.risk_score * 100}%` }"
                    />
                  </div>
                  <span
                    class="text-sm font-bold tabular-nums min-w-[36px] text-right"
                    :class="getScoreTextClass(tx.risk_score)"
                  >
                    {{ tx.risk_score.toFixed(2) }}
                  </span>
                </div>
              </td>

              <!-- Status -->
              <td class="px-4 py-3.5">
                <span
                  class="inline-flex px-2.5 py-1 text-xs font-medium rounded-full capitalize"
                  :class="statusBadgeClasses[tx.status]"
                >
                  {{ tx.status }}
                </span>
              </td>

              <!-- Date -->
              <td class="px-4 py-3.5">
                <span class="text-sm text-gray-500">{{ formatDate(tx.created_at, 'MMM dd, HH:mm') }}</span>
              </td>

              <!-- Actions -->
              <td class="px-4 py-3.5 text-right" @click.stop>
                <CommonActionDropdown :actions="getRowActions(tx)" />
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="paginatedTransactions.length === 0">
              <td colspan="7" class="px-4 py-12 text-center">
                <Icon icon="lucide:inbox" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p class="text-gray-500 text-sm">No withdrawals found matching your filters</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
        <p class="text-sm text-gray-600">
          Showing {{ paginatedTransactions.length }} of {{ filteredTransactions.length }} withdrawals
        </p>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="currentPage <= 1"
            @click="currentPage--"
          >
            Previous
          </button>
          <span class="text-sm text-gray-600 px-2">
            Page {{ currentPage }} of {{ totalPages || 1 }}
          </span>
          <button
            class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="currentPage >= totalPages"
            @click="currentPage++"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <PayoutReviewModal
      :visible="showPayoutReview"
      :transaction="selectedTransaction"
      @close="showPayoutReview = false; selectedTransaction = null"
      @approve="handleApprove"
      @block="handleBlock"
    />

    <FlagModal
      :visible="showFlagModal"
      :transaction-id="selectedTransaction?.id ?? ''"
      :customer-name="selectedTransaction?.customer.name ?? ''"
      @close="showFlagModal = false; selectedTransaction = null"
      @submit="handleFlag"
    />

    <CustomerSummaryModal
      :visible="showCustomerSummary"
      :transaction="selectedTransaction"
      @close="showCustomerSummary = false; selectedTransaction = null"
    />
  </div>
</template>
