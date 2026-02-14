import { formatCurrency } from '~/utils/formatters'

export interface WithdrawalMethod {
  id: string
  name: string
  icon: string
  processingTime: string
  fee: string
  feeAmount: number
  minAmount: number
  maxAmount: number
}

export interface CustomerAccount {
  id: string
  name: string
  country: string
  label: string
}

interface EvalResult {
  decision: 'approved' | 'escalated' | 'blocked'
}

export const WITHDRAWAL_METHODS: WithdrawalMethod[] = [
  { id: 'bank-transfer', name: 'Bank Transfer', icon: 'lucide:building', processingTime: '1-3 business days', fee: '0%', feeAmount: 0, minAmount: 50, maxAmount: 100000 },
  { id: 'wire', name: 'Wire Transfer', icon: 'lucide:building', processingTime: '3-5 business days', fee: '$35 flat', feeAmount: 35, minAmount: 500, maxAmount: 500000 },
  { id: 'card', name: 'Card Refund', icon: 'lucide:credit-card', processingTime: '3-5 business days', fee: '1.5%', feeAmount: 0, minAmount: 10, maxAmount: 25000 },
  { id: 'ewallet', name: 'E-Wallet', icon: 'lucide:wallet', processingTime: '1-2 business days', fee: '1%', feeAmount: 0, minAmount: 10, maxAmount: 10000 },
  { id: 'crypto', name: 'Crypto (BTC/ETH)', icon: 'lucide:bitcoin', processingTime: '10-60 minutes', fee: 'Network fee', feeAmount: 0, minAmount: 50, maxAmount: 200000 },
]

const FEE_RATES: Record<string, number> = {
  wire: 35,
  card: 0.015,
  ewallet: 0.01,
  crypto: 0.001,
}

function calculateFee(method: WithdrawalMethod, amount: number): number {
  if (amount <= 0) return 0
  if (method.id === 'wire') return FEE_RATES.wire
  return (FEE_RATES[method.id] ?? 0) * amount
}

export function useWithdrawal() {
  const accounts = ref<CustomerAccount[]>([])
  const loadingAccounts = ref(true)
  const selectedMethod = ref<WithdrawalMethod | null>(null)
  const selectedAccount = ref('')
  const amount = ref('')
  const recipientName = ref('')
  const recipientAccount = ref('')
  const isSubmitting = ref(false)
  const showSuccess = ref(false)
  const showFraudNotice = ref(false)
  const evalResult = ref<EvalResult | null>(null)

  const currentAccount = computed(() =>
    accounts.value.find(a => a.id === selectedAccount.value),
  )

  const parsedAmount = computed(() => {
    const val = parseFloat(amount.value)
    return isNaN(val) ? 0 : val
  })

  const calculatedFee = computed(() =>
    selectedMethod.value ? calculateFee(selectedMethod.value, parsedAmount.value) : 0,
  )

  const receiveAmount = computed(() =>
    parsedAmount.value > 0 ? parsedAmount.value - calculatedFee.value : 0,
  )

  const amountError = computed(() => {
    if (!selectedMethod.value || !amount.value) return ''
    if (parsedAmount.value < selectedMethod.value.minAmount)
      return `Minimum withdrawal is ${formatCurrency(selectedMethod.value.minAmount)}`
    if (parsedAmount.value > selectedMethod.value.maxAmount)
      return `Maximum withdrawal is ${formatCurrency(selectedMethod.value.maxAmount)}`
    return ''
  })

  const canSubmit = computed(() =>
    !!selectedMethod.value
    && parsedAmount.value > 0
    && !amountError.value
    && !!selectedAccount.value
    && !!recipientName.value.trim()
    && !!recipientAccount.value.trim()
    && !isSubmitting.value,
  )

  async function fetchCustomers(): Promise<void> {
    try {
      const data = await $fetch<{ id: string; name: string; country: string }[]>('/api/customers')
      accounts.value = data.map(c => ({
        id: c.id,
        name: c.name,
        country: c.country,
        label: `${c.name} (${c.country})`,
      }))
      if (accounts.value.length > 0) {
        selectedAccount.value = accounts.value[0].id
      }
    } catch {
      accounts.value = []
    } finally {
      loadingAccounts.value = false
    }
  }

  function resetForm(): void {
    amount.value = ''
    recipientName.value = ''
    recipientAccount.value = ''
    selectedMethod.value = null
  }

  async function handleSubmit(): Promise<void> {
    if (!canSubmit.value) return
    isSubmitting.value = true
    showFraudNotice.value = true
    evalResult.value = null

    try {
      const result = await $fetch<EvalResult>('/api/withdrawals/investigate', {
        method: 'POST',
        body: {
          withdrawal_id: crypto.randomUUID(),
          customer_id: selectedAccount.value,
          amount: parsedAmount.value,
          recipient_name: recipientName.value,
          recipient_account: recipientAccount.value,
          ip_address: '203.0.113.42',
          device_fingerprint: 'demo-device-001',
          customer_country: currentAccount.value?.country || 'MYS',
        },
      })
      isSubmitting.value = false
      showFraudNotice.value = false
      evalResult.value = result
    } catch {
      await new Promise(resolve => setTimeout(resolve, 2500))
      isSubmitting.value = false
      showFraudNotice.value = false
      showSuccess.value = true
      setTimeout(() => {
        showSuccess.value = false
        resetForm()
      }, 3000)
    }
  }

  function dismissResult(): void {
    evalResult.value = null
    resetForm()
  }

  onMounted(fetchCustomers)

  return {
    accounts,
    loadingAccounts,
    selectedMethod,
    selectedAccount,
    amount,
    recipientName,
    recipientAccount,
    isSubmitting,
    showSuccess,
    showFraudNotice,
    evalResult,
    currentAccount,
    parsedAmount,
    calculatedFee,
    receiveAmount,
    amountError,
    canSubmit,
    handleSubmit,
    dismissResult,
  }
}
