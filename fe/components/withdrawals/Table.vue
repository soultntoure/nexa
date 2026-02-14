<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

defineProps<{
  transactions: Transaction[]
  getRowActions: (tx: Transaction) => { label: string; icon: string; color?: string; handler: () => void }[]
}>()

const emit = defineEmits<{
  'row-click': [tx: Transaction]
}>()

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
</script>

<template>
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
            v-for="tx in transactions"
            :key="tx.id"
            class="hover:bg-gray-50/50 transition-colors cursor-pointer"
            @click="emit('row-click', tx)"
          >
            <!-- Customer -->
            <td class="px-4 py-3.5">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-primary-50 rounded-full flex items-center justify-center shrink-0">
                  <span class="text-primary-700 font-medium text-xs">
                    {{ tx.customer.name.split(' ').map((n: string) => n[0]).join('') }}
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
          <tr v-if="transactions.length === 0">
            <td colspan="7" class="px-4 py-12 text-center">
              <Icon icon="lucide:inbox" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p class="text-gray-500 text-sm">No withdrawals found matching your filters</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination slot -->
    <slot name="pagination" />
  </div>
</template>
