<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction, TransactionStatus } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

const props = defineProps<{
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
  checkedIds: Set<string>
}>()

const emit = defineEmits<{
  select: [tx: Transaction]
  'update:selectedStatus': [value: TransactionStatus]
  'update:searchQuery': [value: string]
  'update:dateFrom': [value: string]
  'update:dateTo': [value: string]
  'update:currentPage': [value: number]
  'toggle-check': [id: string]
  'toggle-all': []
}>()

const showDateFilter = ref(false)

const statusTabs: { key: TransactionStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'approved', label: 'Approved' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'blocked', label: 'Blocked' },
]

const statusBadgeClasses: Record<string, string> = {
  pending: 'border-[#EBEBEB] text-gray-600',
  approved: 'border-[#EBEBEB] text-gray-600',
  escalated: 'border-[#EBEBEB] text-gray-600',
  blocked: 'border-[#EBEBEB] text-gray-600',
}

const statusIcons: Record<string, { icon: string; color: string; isCustom?: boolean }> = {
  pending: { icon: 'lucide:clock', color: 'text-white bg-gray-400' },
  approved: { icon: 'lucide:check', color: 'text-white bg-green-500' },
  escalated: { icon: '/icons/alert.svg', color: 'text-white bg-yellow-500', isCustom: true },
  blocked: { icon: 'lucide:x', color: 'text-white bg-red-500' },
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
      </button>
    </div>

    <!-- Results Count + Select All -->
    <div class="shrink-0 flex items-center justify-between px-4 py-2 border-b border-gray-100">
      <div class="flex items-center gap-2">
        <input
          type="checkbox"
          class="rounded text-primary-600 focus:ring-primary-500 cursor-pointer"
          :checked="transactions.length > 0 && transactions.every(t => checkedIds.has(t.id))"
          :indeterminate="transactions.some(t => checkedIds.has(t.id)) && !transactions.every(t => checkedIds.has(t.id))"
          @change="emit('toggle-all')"
        >
        <p class="text-xs text-gray-500">
          <span class="font-medium text-gray-700">{{ totalCount }}</span> results
        </p>
      </div>
    </div>

    <!-- Scrollable Card List -->
    <div class="flex-1 overflow-y-auto">
      <div
        v-for="tx in transactions"
        :key="tx.id"
        class="border-b border-gray-100 px-4 py-3.5 cursor-pointer transition-all"
        :class="selectedId === tx.id
          ? 'bg-gray-100'
          : 'hover:bg-gray-50'"
        @click="emit('select', tx)"
      >
        <!-- Customer Name + Risk Score -->
        <div class="flex items-start justify-between mb-1.5">
          <div class="flex items-start gap-2 min-w-0">
            <input
              type="checkbox"
              class="mt-1 rounded text-primary-600 focus:ring-primary-500 cursor-pointer shrink-0"
              :checked="checkedIds.has(tx.id)"
              @click.stop="emit('toggle-check', tx.id)"
            >
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ tx.customer.name }}</p>
              <p class="text-xs text-gray-500 truncate">{{ tx.customer.email }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0 ml-2">
            <span
              class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border capitalize"
              :class="statusBadgeClasses[tx.status]"
            >
              <span class="flex h-4 w-4 items-center justify-center rounded-full" :class="statusIcons[tx.status]?.color">
                <img v-if="statusIcons[tx.status]?.isCustom" :src="statusIcons[tx.status]?.icon" alt="" class="h-2.5 w-2.5 brightness-0 invert" />
                <Icon v-else :icon="statusIcons[tx.status]?.icon || 'lucide:circle'" class="h-2.5 w-2.5" />
              </span>
              {{ tx.status }}
            </span>
          </div>
        </div>

        <!-- Amount + Method -->
        <div class="flex items-center justify-between mb-2 ml-0">
          <span class="text-sm font-semibold text-gray-900">{{ formatCurrency(tx.amount, tx.currency) }}</span>
          <span class="text-xs text-gray-400">{{ formatDate(tx.created_at, 'MMM dd, HH:mm') }}</span>
        </div>

        <!-- Risk Score Bar -->
        <div class="flex items-center gap-2 ml-0">
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
