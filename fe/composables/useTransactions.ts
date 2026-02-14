export interface RiskIndicator {
  name: string
  icon: string
  score: number
  weight: number
  confidence: number
  reasoning: string
  evidence: Record<string, unknown>
}

export interface Transaction {
  id: string
  withdrawal_id: string
  evaluation_id: string | null
  customer: {
    external_id: string
    name: string
    email: string
    country: string
    registration_date: string
    account_age_days: number
    total_deposits: number
    total_withdrawals: number
    account_type: string
  }
  amount: number
  currency: string
  payment_method: 'card' | 'ewallet' | 'bank' | 'crypto'
  recipient: {
    name: string
    account_number: string
    bank: string
  }
  ip_address: string
  device: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'approved' | 'escalated' | 'blocked'
  indicators: RiskIndicator[]
  triage?: {
    constellation_analysis: string
    decision: string
    decision_reasoning: string
    confidence: number
    risk_score: number
    assignments: { investigator: string; priority: string }[]
    elapsed_s: number
  }
  investigators?: {
    investigator_name: string
    display_name: string
    score: number
    confidence: number
    reasoning: string
    elapsed_s: number
  }[]
  created_at: string
  updated_at: string
}

export type TransactionStatus = 'all' | 'pending' | 'approved' | 'escalated' | 'blocked'

export function useTransactions() {
  const transactions = ref<Transaction[]>([])
  const selectedStatus = ref<TransactionStatus>('all')
  const searchQuery = ref('')
  const currentPage = ref(1)
  const pageSize = ref(10)
  const dateFrom = ref('')
  const dateTo = ref('')
  const isLoading = ref(false)

  async function fetchTransactions() {
    isLoading.value = true
    try {
      const all: Transaction[] = []
      let page = 1
      let totalPages = 1
      do {
        const data = await $fetch<{ items: Transaction[]; total_pages: number }>('/api/transactions', {
          params: { page, page_size: 100 },
        })
        if (data?.items?.length) all.push(...data.items)
        totalPages = data?.total_pages ?? 1
        page++
      } while (page <= totalPages)
      transactions.value = all
    }
    catch {
      // BE unavailable
    }
    finally {
      isLoading.value = false
    }
  }

  // Poll every 10s (handles initial fetch + auto-refresh)
  usePolling(fetchTransactions, 10000)

  const filteredTransactions = computed(() => {
    let result = transactions.value

    if (selectedStatus.value !== 'all') {
      result = result.filter(t => t.status === selectedStatus.value)
    }

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(t =>
        t.customer.name.toLowerCase().includes(query)
        || t.customer.email.toLowerCase().includes(query)
        || t.id.toLowerCase().includes(query),
      )
    }

    if (dateFrom.value) {
      result = result.filter(t => t.created_at >= dateFrom.value)
    }
    if (dateTo.value) {
      result = result.filter(t => t.created_at <= dateTo.value)
    }

    result = [...result].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    return result
  })

  const paginatedTransactions = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return filteredTransactions.value.slice(start, start + pageSize.value)
  })

  const totalPages = computed(() => Math.ceil(filteredTransactions.value.length / pageSize.value))

  const statusCounts = computed(() => ({
    all: transactions.value.length,
    pending: transactions.value.filter(t => t.status === 'pending').length,
    approved: transactions.value.filter(t => t.status === 'approved').length,
    escalated: transactions.value.filter(t => t.status === 'escalated').length,
    blocked: transactions.value.filter(t => t.status === 'blocked').length,
  }))

  function updateTransactionStatus(id: string, newStatus: Transaction['status']) {
    const tx = transactions.value.find(t => t.id === id)
    if (tx) {
      tx.status = newStatus
      tx.updated_at = new Date().toISOString()
    }
  }

  function exportCSV() {
    const headers = ['ID', 'Customer', 'Email', 'Amount', 'Currency', 'Method', 'Risk Score', 'Status', 'Created']
    const rows = filteredTransactions.value.map(t => [
      t.id,
      t.customer.name,
      t.customer.email,
      t.amount.toString(),
      t.currency,
      t.payment_method,
      t.risk_score.toString(),
      t.status,
      t.created_at,
    ])

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `transactions-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    transactions,
    selectedStatus,
    searchQuery,
    currentPage,
    pageSize,
    dateFrom,
    dateTo,
    filteredTransactions,
    paginatedTransactions,
    totalPages,
    statusCounts,
    isLoading,
    updateTransactionStatus,
    fetchTransactions,
    exportCSV,
  }
}
