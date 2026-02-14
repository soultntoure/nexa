<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction, TransactionStatus } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

defineProps<{
  transactions: Transaction[]
  selectedId: string | null
  selectedStatus: TransactionStatus
  statusCounts: Record<TransactionStatus, number>
  searchQuery: string
  dateFrom: string
  dateTo: string
  currentPage: number
  totalPages: number
  shownCount: number
  totalCount: number
}>()

const emit = defineEmits<{
  select: [tx: Transaction]
  'update:selectedStatus': [value: TransactionStatus]
  'update:searchQuery': [value: string]
  'update:dateFrom': [value: string]
  'update:dateTo': [value: string]
  'update:currentPage': [value: number]
}>()

const showDateFilter = ref(false)

const statusTabs: { key: TransactionStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'blocked', label: 'Blocked' },
]

const statusBadgeClasses: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  approved: 'bg-green-100 text-green-700',
  escalated: 'bg-yellow-100 text-yellow-700',
  blocked: 'bg-red-100 text-red-700',
}

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

function selectStatus(key: TransactionStatus) {
  emit('update:selectedStatus', key)
  emit('update:currentPage', 1)
}
</script>

<template>
  <div class="flex flex-col h-full bg-white">
    <!-- Search Header -->
    <div class="shrink-0 p-3 border-b border-gray-200">
      <div class="relative">
        <Icon icon="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          :value="searchQuery"
          type="text"
          placeholder="Search by name, email, or ID..."
          class="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        >
        <button
          class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md transition-colors"
          :class="showDateFilter ? 'bg-primary-100 text-primary-600' : 'text-gray-400 hover:text-gray-600'"
          @click="showDateFilter = !showDateFilter"
        >
          <Icon icon="lucide:sliders-horizontal" class="w-4 h-4" />
        </button>
      </div>

      <!-- Date Filter (collapsible) -->
      <div v-if="showDateFilter" class="flex items-center gap-2 mt-2">
        <input
          :value="dateFrom"
          type="date"
          class="flex-1 px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          @input="emit('update:dateFrom', ($event.target as HTMLInputElement).value)"
        >
        <span class="text-gray-400 text-xs">to</span>
        <input
          :value="dateTo"
          type="date"
          class="flex-1 px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          @input="emit('update:dateTo', ($event.target as HTMLInputElement).value)"
        >
      </div>
    </div>

    <!-- Status Filter Pills -->
    <div class="shrink-0 flex items-center gap-1.5 px-3 py-2.5 border-b border-gray-200 overflow-x-auto">
      <button
        v-for="tab in statusTabs"
        :key="tab.key"
        class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-full border whitespace-nowrap transition-all"
        :class="selectedStatus === tab.key
          ? 'bg-primary-50 text-primary-700 border-primary-200'
          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'"
        @click="selectStatus(tab.key)"
      >
        {{ tab.label }}
        <span
          class="px-1.5 py-0.5 text-[10px] rounded-full"
          :class="selectedStatus === tab.key ? 'bg-primary-200 text-primary-800' : 'bg-gray-100 text-gray-500'"
        >
          {{ statusCounts[tab.key] }}
        </span>
      </button>
    </div>

    <!-- Results Count -->
    <div class="shrink-0 flex items-center justify-between px-4 py-2 border-b border-gray-100">
      <p class="text-xs text-gray-500">
        <span class="font-medium text-gray-700">{{ totalCount }}</span> results
      </p>
    </div>

    <!-- Scrollable Card List -->
    <div class="flex-1 overflow-y-auto">
      <div
        v-for="tx in transactions"
        :key="tx.id"
        class="border-b border-gray-100 px-4 py-3.5 cursor-pointer transition-all"
        :class="selectedId === tx.id
          ? 'bg-blue-50 border-l-[3px] border-l-blue-500'
          : 'hover:bg-gray-50 border-l-[3px] border-l-transparent'"
        @click="emit('select', tx)"
      >
        <!-- Customer Name + Risk Score -->
        <div class="flex items-start justify-between mb-1.5">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 bg-primary-50 rounded-full flex items-center justify-center shrink-0">
              <span class="text-primary-700 font-semibold text-[10px]">
                {{ tx.customer.name.split(' ').map((n: string) => n[0]).join('') }}
              </span>
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ tx.customer.name }}</p>
              <p class="text-xs text-gray-500 truncate">{{ tx.customer.email }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0 ml-2">
            <Icon :icon="paymentMethodIcons[tx.payment_method] || 'lucide:credit-card'" class="w-3.5 h-3.5 text-gray-400" />
            <span
              class="inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full capitalize"
              :class="statusBadgeClasses[tx.status]"
            >
              {{ tx.status }}
            </span>
          </div>
        </div>

        <!-- Amount + Method -->
        <div class="flex items-center gap-2 mb-2 ml-[42px]">
          <span class="text-sm font-semibold text-gray-900">{{ formatCurrency(tx.amount, tx.currency) }}</span>
          <span class="text-gray-300">&middot;</span>
          <span class="text-xs text-gray-500 capitalize">{{ tx.payment_method }}</span>
          <span class="text-gray-300">&middot;</span>
          <span class="text-xs text-gray-400">{{ formatDate(tx.created_at, 'MMM dd, HH:mm') }}</span>
        </div>

        <!-- Risk Score Bar -->
        <div class="flex items-center gap-2 ml-[42px]">
          <div class="flex-1 bg-gray-200 rounded-full h-1">
            <div
              class="h-1 rounded-full transition-all"
              :class="getScoreBarClass(tx.risk_score)"
              :style="{ width: `${tx.risk_score * 100}%` }"
            />
          </div>
          <span
            class="text-xs font-bold tabular-nums min-w-[32px] text-right"
            :class="getScoreTextClass(tx.risk_score)"
          >
            {{ tx.risk_score.toFixed(2) }}
          </span>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="transactions.length === 0" class="flex flex-col items-center justify-center py-16 px-4">
        <Icon icon="lucide:inbox" class="w-12 h-12 text-gray-300 mb-3" />
        <p class="text-gray-500 text-sm">No withdrawals found</p>
        <p class="text-gray-400 text-xs mt-1">Try adjusting your filters</p>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="transactions.length > 0" class="shrink-0 flex items-center justify-between px-4 py-2.5 border-t border-gray-200 bg-gray-50">
      <p class="text-xs text-gray-500">
        {{ shownCount }} of {{ totalCount }}
      </p>
      <div class="flex items-center gap-1.5">
        <button
          class="px-2.5 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="currentPage <= 1"
          @click="emit('update:currentPage', currentPage - 1)"
        >
          <Icon icon="lucide:chevron-left" class="w-3.5 h-3.5" />
        </button>
        <span class="text-xs text-gray-500 px-1">{{ currentPage }} / {{ totalPages || 1 }}</span>
        <button
          class="px-2.5 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="currentPage >= totalPages"
          @click="emit('update:currentPage', currentPage + 1)"
        >
          <Icon icon="lucide:chevron-right" class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </div>
</template>
