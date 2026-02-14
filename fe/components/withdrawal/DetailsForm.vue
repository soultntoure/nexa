<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { WithdrawalMethod, CustomerAccount } from '~/composables/useWithdrawal'
import { formatCurrency } from '~/utils/formatters'

defineProps<{
  selectedMethod: WithdrawalMethod | null
  accounts: CustomerAccount[]
  loadingAccounts: boolean
  currentAccount: CustomerAccount | undefined
  parsedAmount: number
  calculatedFee: number
  receiveAmount: number
  amountError: string
  canSubmit: boolean
  isSubmitting: boolean
}>()

const selectedAccount = defineModel<string>('selectedAccount', { default: '' })
const amount = defineModel<string>('amount', { default: '' })
const recipientName = defineModel<string>('recipientName', { default: '' })
const recipientAccount = defineModel<string>('recipientAccount', { default: '' })

const emit = defineEmits<{
  submit: []
}>()
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-5">
      <h3 class="text-base font-semibold text-gray-900">Withdrawal Details</h3>

      <!-- Account Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1.5">From Account</label>
        <select
          v-model="selectedAccount"
          :disabled="loadingAccounts"
          class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
        >
          <option v-if="loadingAccounts" value="" disabled>Loading accounts...</option>
          <option v-for="account in accounts" :key="account.id" :value="account.id">
            {{ account.label }}
          </option>
        </select>
        <p v-if="currentAccount" class="mt-1 text-xs text-gray-500">
          Customer ID: <span class="font-medium text-gray-700">{{ currentAccount.id }}</span>
        </p>
      </div>

      <!-- Amount Input -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1.5">Amount (USD)</label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
          <input
            v-model="amount"
            type="number"
            placeholder="0.00"
            step="0.01"
            class="w-full pl-7 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            :class="amountError ? 'border-red-300' : 'border-gray-300'"
          >
        </div>
        <p v-if="amountError" class="mt-1 text-xs text-red-500">{{ amountError }}</p>
      </div>

      <!-- Recipient Details -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1.5">Recipient Name</label>
        <input
          v-model="recipientName"
          type="text"
          placeholder="Full legal name"
          class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1.5">
          {{ selectedMethod?.id === 'crypto' ? 'Wallet Address' : 'Account Number / IBAN' }}
        </label>
        <input
          v-model="recipientAccount"
          type="text"
          :placeholder="selectedMethod?.id === 'crypto' ? '0x... or bc1...' : 'Enter account number'"
          class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
      </div>

      <!-- Fee Summary -->
      <div v-if="selectedMethod && parsedAmount > 0" class="bg-gray-50 rounded-lg p-3 space-y-2">
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-500">Processing Time</span>
          <span class="font-medium text-gray-900">{{ selectedMethod.processingTime }}</span>
        </div>
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-500">Fee</span>
          <span class="font-medium text-gray-900">{{ calculatedFee > 0 ? formatCurrency(calculatedFee) : 'Free' }}</span>
        </div>
        <div class="flex items-center justify-between text-sm border-t border-gray-200 pt-2 mt-2">
          <span class="text-gray-700 font-medium">You will receive</span>
          <span class="text-lg font-bold text-gray-900">{{ formatCurrency(receiveAmount) }}</span>
        </div>
      </div>

      <!-- Submit -->
      <button
        class="w-full py-3 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        :disabled="!canSubmit"
        @click="emit('submit')"
      >
        <Icon v-if="isSubmitting" icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
        <Icon v-else icon="lucide:arrow-up-circle" class="w-4 h-4" />
        {{ isSubmitting ? 'Evaluating...' : 'Request Withdrawal' }}
      </button>
    </div>

    <!-- Security Note -->
    <div class="bg-blue-50 border border-blue-100 rounded-lg p-4">
      <div class="flex items-start gap-2">
        <Icon icon="lucide:lock" class="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
        <div>
          <p class="text-xs font-medium text-blue-800">Secure Withdrawal</p>
          <p class="text-xs text-blue-600 mt-0.5">Withdrawal requests are subject to identity verification and fraud screening. Processing times may vary.</p>
        </div>
      </div>
    </div>
  </div>
</template>
