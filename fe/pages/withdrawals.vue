<script setup lang="ts">
import type { Transaction } from '~/composables/useTransactions'

useHead({ title: 'Nexa' })

const {
  transactions: allTransactions,
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
const { openWithContext } = useChatWidgetState()

const route = useRoute()
const selectedTransaction = ref<Transaction | null>(null)
const showFlagModal = ref(false)
const showCustomerSummary = ref(false)
const checkedIds = ref<Set<string>>(new Set())
const isBatchSubmitting = ref(false)

function toggleCheck(id: string) {
  const next = new Set(checkedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  checkedIds.value = next
}

function toggleAll() {
  const allChecked = paginatedTransactions.value.every(t => checkedIds.value.has(t.id))
  const next = new Set(checkedIds.value)
  if (allChecked) {
    paginatedTransactions.value.forEach(t => next.delete(t.id))
  } else {
    paginatedTransactions.value.forEach(t => next.add(t.id))
  }
  checkedIds.value = next
}

function clearChecked() {
  checkedIds.value = new Set()
}

const checkedTransactions = computed(() =>
  allTransactions.value.filter(t => checkedIds.value.has(t.id)),
)

async function handleBatchAction(action: 'approved' | 'blocked', reason: string) {
  if (checkedTransactions.value.length === 0) return
  isBatchSubmitting.value = true
  try {
    await $fetch('/api/payout/batch-decision', {
      method: 'POST',
      body: {
        items: checkedTransactions.value.map(t => ({
          withdrawal_id: t.withdrawal_id,
          evaluation_id: t.evaluation_id,
        })),
        officer_id: 'officer-demo-001',
        action,
        reason,
      },
    })
    checkedTransactions.value.forEach(t => updateTransactionStatus(t.id, action))
    clearChecked()
  } catch {
    // batch call failed
  } finally {
    isBatchSubmitting.value = false
  }
}

// Pre-populate filters from query params (e.g. from notification click)
const fromNotification = Boolean(route.query.search)
if (route.query.search) {
  searchQuery.value = String(route.query.search)
}
if (route.query.status) {
  selectedStatus.value = String(route.query.status) as typeof selectedStatus.value
}

// Auto-select first matching transaction when arriving from notification
if (fromNotification) {
  const stop = watch(filteredTransactions, (txs) => {
    if (txs.length > 0 && !selectedTransaction.value) {
      selectedTransaction.value = txs[0]
      stop()
    }
  }, { immediate: true })
}

function selectTransaction(tx: Transaction) {
  selectedTransaction.value = tx
}

function closeDetail() {
  selectedTransaction.value = null
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

async function handleApprove(justification: string): Promise<void> {
  if (!selectedTransaction.value) return
  await submitDecisionToBE(selectedTransaction.value, 'approved', justification)
  updateTransactionStatus(selectedTransaction.value.id, 'approved')
}

async function handleBlock(justification: string, lockConnected: boolean): Promise<void> {
  if (!selectedTransaction.value) return
  const tx = selectedTransaction.value
  await submitDecisionToBE(tx, 'blocked', justification)
  updateTransactionStatus(tx.id, 'blocked')

  if (lockConnected) {
    try {
      await $fetch('/api/alerts/card-lockdown', {
        method: 'POST',
        body: {
          customer_id: tx.customer.external_id,
          risk_score: tx.risk_score,
          admin_id: 'officer-demo-001',
        },
      })
    } catch {
      // lockdown call failed — block still proceeded
    }
  }

  selectedTransaction.value = null
}

function handleFlag(): void {
  showFlagModal.value = true
}

function handleFlagSubmit(data: { reason: string; notes: string }): void {
  if (selectedTransaction.value) {
    updateTransactionStatus(selectedTransaction.value.id, 'escalated')
  }
  showFlagModal.value = false
}

function handleCustomerProfile(): void {
  showCustomerSummary.value = true
}

function handleDiscuss(): void {
  if (!selectedTransaction.value) return
  const tx = selectedTransaction.value
  setDiscussionFromTransaction(tx)
  openWithContext({
    id: tx.id,
    withdrawal_id: tx.withdrawal_id,
    customer_external_id: tx.customer.external_id,
    customer_name: tx.customer.name,
    customer_email: tx.customer.email,
    amount: tx.amount,
    currency: tx.currency,
    risk_score: tx.risk_score,
    risk_level: tx.risk_level,
    status: tx.status,
    payment_method: tx.payment_method,
    recipient_name: tx.recipient.name,
    recipient_account: tx.recipient.account_number,
    ip_address: tx.ip_address,
    device: tx.device,
    created_at: tx.created_at,
  })
}
</script>

<template>
  <div class="-m-6 flex overflow-hidden" style="height: 100vh">
    <!-- Left Panel: Card List -->
    <div class="w-[380px] shrink-0 border-r border-gray-200 flex flex-col z-20">
      <WithdrawalsBatchActionBar
        v-if="checkedIds.size > 0"
        :selected-count="checkedIds.size"
        :is-submitting="isBatchSubmitting"
        @batch-approve="(reason) => handleBatchAction('approved', reason)"
        @batch-block="(reason) => handleBatchAction('blocked', reason)"
        @clear="clearChecked"
      />

      <WithdrawalsCardList
        :transactions="paginatedTransactions"
        :selected-id="selectedTransaction?.id ?? null"
        :selected-status="selectedStatus"
        :status-counts="statusCounts"
        :search-query="searchQuery"
        :date-from="dateFrom"
        :date-to="dateTo"
        :current-page="currentPage"
        :total-pages="totalPages"
        :shown-count="paginatedTransactions.length"
        :total-count="filteredTransactions.length"
        :checked-ids="checkedIds"
        @select="selectTransaction"
        @update:selected-status="(v) => { selectedStatus = v; currentPage = 1 }"
        @update:search-query="(v) => { searchQuery = v; currentPage = 1 }"
        @update:date-from="(v) => dateFrom = v"
        @update:date-to="(v) => dateTo = v"
        @update:current-page="(v) => currentPage = v"
        @toggle-check="toggleCheck"
        @toggle-all="toggleAll"
      />
    </div>

    <!-- Right Area: Map + Detail Panel overlay -->
    <div class="flex-1 relative overflow-hidden">
      <!-- Map (always visible, fills the right area) -->
      <ClientOnly>
        <WithdrawalsRiskMap
          :transactions="allTransactions"
          :selected-id="selectedTransaction?.id ?? null"
          @select-marker="selectTransaction"
        />
      </ClientOnly>

      <!-- Detail Panel (overlays on top of map, like Google Maps) -->
      <Transition
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="-translate-x-full opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="-translate-x-full opacity-0"
      >
        <div
          v-if="selectedTransaction"
          class="absolute inset-y-0 left-0 w-[420px] z-[1000] shadow-2xl translate-x-0 opacity-100"
        >
          <WithdrawalsDetailPanel
            :key="selectedTransaction.id"
            :transaction="selectedTransaction"
            @close="closeDetail"
            @approve="handleApprove"
            @block="handleBlock"
            @flag="handleFlag"
            @discuss="handleDiscuss"
            @customer-profile="handleCustomerProfile"
          />
        </div>
      </Transition>

      <!-- Map Legend (bottom-left, above map) -->
      <div class="absolute bottom-6 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg shadow-md px-3 py-2.5 border border-gray-200" :class="selectedTransaction ? 'left-[436px]' : 'left-4'" style="transition: left 0.3s ease">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Risk Level</p>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-green-500 border border-green-600" />
            <span class="text-xs text-gray-600">Low</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-yellow-500 border border-yellow-600" />
            <span class="text-xs text-gray-600">Medium</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-red-500 border border-red-600" />
            <span class="text-xs text-gray-600">High</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modals -->
  <FlagModal
    :visible="showFlagModal"
    :transaction-id="selectedTransaction?.id ?? ''"
    :customer-name="selectedTransaction?.customer.name ?? ''"
    @close="showFlagModal = false"
    @submit="handleFlagSubmit"
  />

  <CustomerSummaryModal
    :visible="showCustomerSummary"
    :transaction="selectedTransaction"
    @close="showCustomerSummary = false"
  />

</template>
