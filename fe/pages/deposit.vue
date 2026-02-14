<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { formatCurrency } from '~/utils/formatters'

useHead({ title: 'Deposit - Nexa' })

interface PaymentMethod {
  id: string
  name: string
  icon: string
  category: 'card' | 'bank' | 'ewallet' | 'crypto'
  processingTime: string
  fee: string
  feePercent: number
  minAmount: number
  maxAmount: number
}

const paymentMethods: PaymentMethod[] = [
  { id: 'visa', name: 'Visa', icon: 'lucide:credit-card', category: 'card', processingTime: 'Instant', fee: '2.5%', feePercent: 0.025, minAmount: 10, maxAmount: 50000 },
  { id: 'mastercard', name: 'Mastercard', icon: 'lucide:credit-card', category: 'card', processingTime: 'Instant', fee: '2.5%', feePercent: 0.025, minAmount: 10, maxAmount: 50000 },
  { id: 'bank-transfer', name: 'Bank Transfer', icon: 'lucide:building', category: 'bank', processingTime: '1-3 business days', fee: '0%', feePercent: 0, minAmount: 100, maxAmount: 500000 },
  { id: 'wire', name: 'Wire Transfer', icon: 'lucide:building', category: 'bank', processingTime: '1-5 business days', fee: '$25 flat', feePercent: 0, minAmount: 500, maxAmount: 1000000 },
  { id: 'grabpay', name: 'GrabPay', icon: 'lucide:wallet', category: 'ewallet', processingTime: 'Instant', fee: '1.5%', feePercent: 0.015, minAmount: 10, maxAmount: 5000 },
  { id: 'touchngo', name: "Touch 'n Go", icon: 'lucide:wallet', category: 'ewallet', processingTime: 'Instant', fee: '1.5%', feePercent: 0.015, minAmount: 10, maxAmount: 5000 },
  { id: 'bitcoin', name: 'Bitcoin', icon: 'lucide:bitcoin', category: 'crypto', processingTime: '10-60 minutes', fee: 'Network fee', feePercent: 0.001, minAmount: 50, maxAmount: 100000 },
  { id: 'ethereum', name: 'Ethereum', icon: 'lucide:circle-dot', category: 'crypto', processingTime: '2-10 minutes', fee: 'Gas fee', feePercent: 0.002, minAmount: 50, maxAmount: 100000 },
]

type FilterCategory = 'all' | 'card' | 'bank' | 'ewallet' | 'crypto'

const filterTabs: { key: FilterCategory; label: string; icon: string }[] = [
  { key: 'all', label: 'All', icon: 'lucide:layers' },
  { key: 'card', label: 'Cards', icon: 'lucide:credit-card' },
  { key: 'bank', label: 'Banks', icon: 'lucide:building' },
  { key: 'ewallet', label: 'E-Wallets', icon: 'lucide:wallet' },
  { key: 'crypto', label: 'Crypto', icon: 'lucide:bitcoin' },
]

const selectedFilter = ref<FilterCategory>('all')
const selectedMethod = ref<PaymentMethod | null>(null)
const amount = ref('')
const selectedAccount = ref('MT5-001')
const isSubmitting = ref(false)
const showSuccess = ref(false)

const accounts = [
  { id: 'MT5-001', label: 'MT5 - Live #001', balance: 12450.00 },
  { id: 'MT5-002', label: 'MT5 - Live #002', balance: 3200.50 },
  { id: 'MT4-001', label: 'MT4 - Standard #001', balance: 890.25 },
]

const filteredMethods = computed(() => {
  if (selectedFilter.value === 'all') return paymentMethods
  return paymentMethods.filter(m => m.category === selectedFilter.value)
})

const parsedAmount = computed(() => {
  const val = parseFloat(amount.value)
  return isNaN(val) ? 0 : val
})

const feeAmount = computed(() => {
  if (!selectedMethod.value || parsedAmount.value <= 0) return 0
  if (selectedMethod.value.id === 'wire') return 25
  return parsedAmount.value * selectedMethod.value.feePercent
})

const receiveAmount = computed(() => {
  if (parsedAmount.value <= 0) return 0
  return parsedAmount.value - feeAmount.value
})

const amountError = computed(() => {
  if (!selectedMethod.value || !amount.value) return ''
  if (parsedAmount.value < selectedMethod.value.minAmount)
    return `Minimum deposit is ${formatCurrency(selectedMethod.value.minAmount)}`
  if (parsedAmount.value > selectedMethod.value.maxAmount)
    return `Maximum deposit is ${formatCurrency(selectedMethod.value.maxAmount)}`
  return ''
})

const canSubmit = computed(() => {
  return selectedMethod.value
    && parsedAmount.value > 0
    && !amountError.value
    && selectedAccount.value
    && !isSubmitting.value
})

function selectMethod(method: PaymentMethod) {
  selectedMethod.value = method
}

async function handleSubmit() {
  if (!canSubmit.value) return
  isSubmitting.value = true
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1500))
  isSubmitting.value = false
  showSuccess.value = true
  setTimeout(() => {
    showSuccess.value = false
    amount.value = ''
    selectedMethod.value = null
  }, 3000)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Deposit Funds</h1>
      <p class="text-sm text-gray-500 mt-1">Add funds to your trading account using your preferred payment method</p>
    </div>

    <!-- Success Message -->
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showSuccess" class="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
        <Icon icon="lucide:check-circle" class="w-5 h-5 text-green-600 shrink-0" />
        <div>
          <p class="text-sm font-medium text-green-800">Deposit initiated successfully!</p>
          <p class="text-xs text-green-600 mt-0.5">Your funds will be available within the processing time.</p>
        </div>
      </div>
    </Transition>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Payment Methods (Left 2/3) -->
      <div class="lg:col-span-2 space-y-4">
        <!-- Filter Tabs -->
        <div class="flex items-center gap-1 bg-gray-100 p-1 rounded-lg w-fit">
          <button
            v-for="tab in filterTabs"
            :key="tab.key"
            class="flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-all"
            :class="selectedFilter === tab.key
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'"
            @click="selectedFilter = tab.key"
          >
            <Icon :icon="tab.icon" class="w-4 h-4" />
            {{ tab.label }}
          </button>
        </div>

        <!-- Method Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            v-for="method in filteredMethods"
            :key="method.id"
            class="flex items-center gap-4 p-4 bg-white rounded-xl border-2 transition-all text-left"
            :class="selectedMethod?.id === method.id
              ? 'border-primary-500 bg-primary-50/30 shadow-sm'
              : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'"
            @click="selectMethod(method)"
          >
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
              :class="selectedMethod?.id === method.id ? 'bg-primary-100' : 'bg-gray-100'"
            >
              <Icon
                :icon="method.icon"
                class="w-6 h-6"
                :class="selectedMethod?.id === method.id ? 'text-primary-600' : 'text-gray-500'"
              />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-900">{{ method.name }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ method.processingTime }}</p>
              <div class="flex items-center gap-3 mt-1 text-xs text-gray-400">
                <span>Fee: {{ method.fee }}</span>
                <span>Min: {{ formatCurrency(method.minAmount) }}</span>
              </div>
            </div>
            <div v-if="selectedMethod?.id === method.id">
              <Icon icon="lucide:check-circle-2" class="w-5 h-5 text-primary-600" />
            </div>
          </button>
        </div>
      </div>

      <!-- Deposit Form (Right 1/3) -->
      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-5">
          <h3 class="text-base font-semibold text-gray-900">Deposit Details</h3>

          <!-- Account Selection -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">Trading Account</label>
            <select
              v-model="selectedAccount"
              class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option v-for="account in accounts" :key="account.id" :value="account.id">
                {{ account.label }} ({{ formatCurrency(account.balance) }})
              </option>
            </select>
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

          <!-- Processing Info -->
          <div v-if="selectedMethod" class="bg-gray-50 rounded-lg p-3 space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-500">Processing Time</span>
              <span class="font-medium text-gray-900">{{ selectedMethod.processingTime }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-500">Fee</span>
              <span class="font-medium text-gray-900">{{ feeAmount > 0 ? formatCurrency(feeAmount) : 'Free' }}</span>
            </div>
            <div class="flex items-center justify-between text-sm border-t border-gray-200 pt-2 mt-2">
              <span class="text-gray-700 font-medium">You will receive</span>
              <span class="text-lg font-bold text-gray-900">{{ formatCurrency(receiveAmount) }}</span>
            </div>
          </div>

          <div v-else class="bg-gray-50 rounded-lg p-4 text-center">
            <Icon icon="lucide:arrow-left" class="w-5 h-5 text-gray-400 mx-auto mb-1" />
            <p class="text-sm text-gray-500">Select a payment method to continue</p>
          </div>

          <!-- Submit -->
          <button
            class="w-full py-3 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            :disabled="!canSubmit"
            @click="handleSubmit"
          >
            <Icon v-if="isSubmitting" icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
            <Icon v-else icon="lucide:arrow-down-circle" class="w-4 h-4" />
            {{ isSubmitting ? 'Processing...' : 'Deposit Now' }}
          </button>
        </div>

        <!-- Security Note -->
        <div class="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <div class="flex items-start gap-2">
            <Icon icon="lucide:shield-check" class="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
            <div>
              <p class="text-xs font-medium text-blue-800">Secure Transaction</p>
              <p class="text-xs text-blue-600 mt-0.5">All deposits are encrypted and processed through our secure payment gateway. Funds are held in segregated accounts.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
