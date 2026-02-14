<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { Transaction } from '~/composables/useTransactions'
import { formatCurrency, formatDate } from '~/utils/formatters'

const props = defineProps<{
  visible: boolean
  transaction: Transaction | null
}>()

const emit = defineEmits<{
  close: []
}>()
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
        <div class="absolute inset-0 bg-black/50" @click="emit('close')" />

        <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-lg">
          <!-- Header -->
          <div class="flex items-center justify-between p-5 border-b border-gray-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <span class="text-blue-700 font-semibold text-sm">
                  {{ transaction.customer.name.split(' ').map(n => n[0]).join('') }}
                </span>
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">{{ transaction.customer.name }}</h3>
                <p class="text-sm text-gray-500">{{ transaction.customer.email }}</p>
              </div>
            </div>
            <button class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors" @click="emit('close')">
              <Icon icon="lucide:x" class="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <!-- Body -->
          <div class="p-5 space-y-5">
            <!-- Account Info -->
            <div class="grid grid-cols-2 gap-4">
              <div class="p-3 bg-gray-50 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Account Type</p>
                <p class="text-sm font-medium text-gray-900">{{ transaction.customer.account_type }}</p>
              </div>
              <div class="p-3 bg-gray-50 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Country</p>
                <p class="text-sm font-medium text-gray-900">{{ transaction.customer.country }}</p>
              </div>
              <div class="p-3 bg-gray-50 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Registered</p>
                <p class="text-sm font-medium text-gray-900">{{ formatDate(transaction.customer.registration_date) }}</p>
              </div>
              <div class="p-3 bg-gray-50 rounded-lg">
                <p class="text-xs text-gray-500 mb-1">Account Age</p>
                <p class="text-sm font-medium text-gray-900">{{ transaction.customer.account_age_days }} days</p>
              </div>
            </div>

            <!-- Financial Summary -->
            <div>
              <h4 class="text-sm font-medium text-gray-700 mb-3">Financial Summary</h4>
              <div class="grid grid-cols-2 gap-4">
                <div class="p-3 bg-green-50 rounded-lg border border-green-100">
                  <div class="flex items-center gap-2 mb-1">
                    <Icon icon="lucide:arrow-down-circle" class="w-4 h-4 text-green-600" />
                    <p class="text-xs text-green-700">Total Deposits</p>
                  </div>
                  <p class="text-lg font-semibold text-green-800">{{ formatCurrency(transaction.customer.total_deposits) }}</p>
                </div>
                <div class="p-3 bg-red-50 rounded-lg border border-red-100">
                  <div class="flex items-center gap-2 mb-1">
                    <Icon icon="lucide:arrow-up-circle" class="w-4 h-4 text-red-600" />
                    <p class="text-xs text-red-700">Total Withdrawals</p>
                  </div>
                  <p class="text-lg font-semibold text-red-800">{{ formatCurrency(transaction.customer.total_withdrawals) }}</p>
                </div>
              </div>
            </div>

            <!-- Withdrawal/Deposit Ratio -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm text-gray-600">Withdrawal Ratio</span>
                <span class="text-sm font-medium" :class="
                  transaction.customer.total_deposits > 0
                    ? (transaction.customer.total_withdrawals / transaction.customer.total_deposits) > 0.8
                      ? 'text-red-600'
                      : (transaction.customer.total_withdrawals / transaction.customer.total_deposits) > 0.5
                        ? 'text-yellow-600'
                        : 'text-green-600'
                    : 'text-gray-600'
                ">
                  {{ transaction.customer.total_deposits > 0
                    ? ((transaction.customer.total_withdrawals / transaction.customer.total_deposits) * 100).toFixed(1)
                    : 0
                  }}%
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                  class="h-2 rounded-full transition-all"
                  :class="
                    transaction.customer.total_deposits > 0
                      ? (transaction.customer.total_withdrawals / transaction.customer.total_deposits) > 0.8
                        ? 'bg-red-500'
                        : (transaction.customer.total_withdrawals / transaction.customer.total_deposits) > 0.5
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      : 'bg-gray-400'
                  "
                  :style="{ width: transaction.customer.total_deposits > 0
                    ? `${Math.min((transaction.customer.total_withdrawals / transaction.customer.total_deposits) * 100, 100)}%`
                    : '0%'
                  }"
                />
              </div>
            </div>

            <!-- Current Transaction -->
            <div class="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <h4 class="text-sm font-medium text-blue-800 mb-2">Current Transaction</h4>
              <div class="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span class="text-blue-600">Amount:</span>
                  <span class="font-medium text-blue-900 ml-1">{{ formatCurrency(transaction.amount, transaction.currency) }}</span>
                </div>
                <div>
                  <span class="text-blue-600">Method:</span>
                  <span class="font-medium text-blue-900 ml-1 capitalize">{{ transaction.payment_method }}</span>
                </div>
                <div>
                  <span class="text-blue-600">Risk Score:</span>
                  <span
                    class="font-medium ml-1"
                    :class="transaction.risk_score >= 0.7 ? 'text-red-600' : transaction.risk_score >= 0.3 ? 'text-yellow-600' : 'text-green-600'"
                  >
                    {{ transaction.risk_score.toFixed(2) }}
                  </span>
                </div>
                <div>
                  <span class="text-blue-600">Status:</span>
                  <span class="font-medium text-blue-900 ml-1 capitalize">{{ transaction.status }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end p-5 border-t border-gray-200">
            <button
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              @click="emit('close')"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
