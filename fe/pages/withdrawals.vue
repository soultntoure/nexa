<script setup lang="ts">
import type { Transaction } from '~/composables/useTransactions'

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
const { setDiscussionFromTransaction } = useWithdrawalDiscussion()

const showPayoutReview = ref(false)
const showFlagModal = ref(false)
const showCustomerSummary = ref(false)
const selectedTransaction = ref<Transaction | null>(null)

function openPayoutReview(tx: Transaction): void {
  selectedTransaction.value = tx
  showPayoutReview.value = true
}

function openFlagModal(tx: Transaction): void {
  selectedTransaction.value = tx
  showFlagModal.value = true
}

function openCustomerSummary(tx: Transaction): void {
  selectedTransaction.value = tx
  showCustomerSummary.value = true
}

async function submitDecisionToBE(tx: Transaction, action: 'approved' | 'blocked', reason: string): Promise<void> {
  try {
    await $fetch('/api/payout/decision', {
      method: 'POST',
      body: {
        withdrawal_id: tx.withdrawal_id,
        evaluation_id: tx.evaluation_id,
        officer_id: 'officer-demo-001',
        action,
        reason,
      },
    })
  } catch {
    // BE call failed — local state update still proceeds
  }
}

async function handleApprove(data: { id: string; justification: string }): Promise<void> {
  const tx = filteredTransactions.value.find(t => t.id === data.id)
  if (tx) await submitDecisionToBE(tx, 'approved', data.justification)
  updateTransactionStatus(data.id, 'approved')
  showPayoutReview.value = false
  selectedTransaction.value = null
}

async function handleBlock(data: { id: string; justification: string }): Promise<void> {
  const tx = filteredTransactions.value.find(t => t.id === data.id)
  if (tx) await submitDecisionToBE(tx, 'blocked', data.justification)
  updateTransactionStatus(data.id, 'blocked')
  showPayoutReview.value = false
  selectedTransaction.value = null
}

async function handleQuickApprove(tx: Transaction): Promise<void> {
  await submitDecisionToBE(tx, 'approved', 'Quick approval by officer')
  updateTransactionStatus(tx.id, 'approved')
}

function handleFlag(data: { reason: string; notes: string }): void {
  if (selectedTransaction.value) {
    updateTransactionStatus(selectedTransaction.value.id, 'escalated')
  }
  showFlagModal.value = false
  selectedTransaction.value = null
}

async function handleQuickBlock(tx: Transaction): Promise<void> {
  await submitDecisionToBE(tx, 'blocked', 'Quick block by officer')
  updateTransactionStatus(tx.id, 'blocked')
}

async function openDiscussionInQuery(tx: Transaction): Promise<void> {
  setDiscussionFromTransaction(tx)
  showPayoutReview.value = false
  selectedTransaction.value = null
  await navigateTo({
    path: '/query',
    query: {
      focus: 'withdrawal',
      withdrawal_id: tx.withdrawal_id || tx.id,
      customer_external_id: tx.customer.external_id,
      customer_name: tx.customer.name,
      customer_email: tx.customer.email,
      amount: String(tx.amount),
      currency: tx.currency,
      risk_score: tx.risk_score.toFixed(2),
      risk_level: tx.risk_level,
      status: tx.status,
      payment_method: tx.payment_method,
      recipient_name: tx.recipient.name,
      recipient_account: tx.recipient.account_number,
      ip_address: tx.ip_address,
      device: tx.device,
      created_at: tx.created_at,
    },
  })
}

async function handleDiscuss(data: { id: string }): Promise<void> {
  const tx = filteredTransactions.value.find(t => t.id === data.id) || selectedTransaction.value
  if (!tx) return
  await openDiscussionInQuery(tx)
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
    <WithdrawalsStatusTabs
      :selected-status="selectedStatus"
      :status-counts="statusCounts"
      @update:selected-status="(v) => { selectedStatus = v; currentPage = 1 }"
    />

    <!-- Search & Date Filter -->
    <WithdrawalsSearchBar
      v-model:search-query="searchQuery"
      v-model:date-from="dateFrom"
      v-model:date-to="dateTo"
      @search="currentPage = 1"
    />

    <!-- Transactions Table -->
    <WithdrawalsTable
      :transactions="paginatedTransactions"
      :get-row-actions="getRowActions"
      @row-click="openPayoutReview"
    >
      <template #pagination>
        <WithdrawalsPagination
          :current-page="currentPage"
          :total-pages="totalPages"
          :shown-count="paginatedTransactions.length"
          :total-count="filteredTransactions.length"
          @update:current-page="(v) => currentPage = v"
        />
      </template>
    </WithdrawalsTable>

    <!-- Modals -->
    <PayoutReviewModal
      :visible="showPayoutReview"
      :transaction="selectedTransaction"
      @close="showPayoutReview = false; selectedTransaction = null"
      @discuss="handleDiscuss"
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
