import type { Alert, LinkedAccount, LockdownResult, FraudPattern } from '~/utils/alertTypes'
import { formatDate } from '~/utils/formatters'

type CardCheckEntry = { shared: boolean; linked_count: number; linked_accounts: LinkedAccount[] }

const MOCK_ALERTS: Alert[] = [
  { id: 'ALT-001', type: 'block', customer_name: 'Sarah Ahmed', account_id: 'ACC-6637', risk_score: 96, indicators: [{ name: 'amount_anomaly', score: 95 }, { name: 'trading_behavior', score: 92 }, { name: 'velocity', score: 88 }], timestamp: new Date(Date.now() - 120000).toISOString(), read: false, amount: 2300, currency: 'USD' },
  { id: 'ALT-002', type: 'escalation', customer_name: 'Marcus Chen', account_id: 'ACC-8821', risk_score: 94, indicators: [{ name: 'amount_anomaly', score: 91 }, { name: 'geographic', score: 85 }, { name: 'device_fingerprint', score: 78 }], timestamp: new Date(Date.now() - 300000).toISOString(), read: false, amount: 4900, currency: 'USD' },
  { id: 'ALT-003', type: 'block', customer_name: 'David Park', account_id: 'ACC-9102', risk_score: 92, indicators: [{ name: 'velocity', score: 94 }, { name: 'geographic', score: 89 }, { name: 'payment_method', score: 76 }], timestamp: new Date(Date.now() - 600000).toISOString(), read: false, amount: 7800, currency: 'USD' },
  { id: 'ALT-004', type: 'escalation', customer_name: 'Elena Petrov', account_id: 'ACC-7744', risk_score: 89, indicators: [{ name: 'payment_method', score: 92 }, { name: 'geographic', score: 87 }, { name: 'card_errors', score: 71 }], timestamp: new Date(Date.now() - 900000).toISOString(), read: true, amount: 3650, currency: 'USD' },
  { id: 'ALT-005', type: 'escalation', customer_name: 'Yuki Tanaka', account_id: 'ACC-5540', risk_score: 91, indicators: [{ name: 'card_errors', score: 93 }, { name: 'velocity', score: 82 }, { name: 'payment_method', score: 79 }], timestamp: new Date(Date.now() - 1500000).toISOString(), read: true, amount: 22100, currency: 'USD' },
  { id: 'ALT-006', type: 'block', customer_name: 'James Wilson', account_id: 'ACC-5519', risk_score: 85, indicators: [{ name: 'trading_behavior', score: 88 }, { name: 'amount_anomaly', score: 82 }, { name: 'recipient', score: 74 }], timestamp: new Date(Date.now() - 2400000).toISOString(), read: true, amount: 6200, currency: 'USD' },
]

const FRAUD_PATTERNS: FraudPattern[] = [
  { name: 'No Trade Pattern', key: 'no_trade', accounts_affected: 12, total_exposure: 45800, confidence: 94 },
  { name: 'Short Trade Abuse', key: 'short_trade', accounts_affected: 8, total_exposure: 23400, confidence: 87 },
  { name: 'Card Testing', key: 'card_testing', accounts_affected: 5, total_exposure: 2100, confidence: 91 },
  { name: 'Velocity Abuse', key: 'velocity', accounts_affected: 3, total_exposure: 67200, confidence: 78 },
]

export function useAlerts() {
  const { data: alertsData, refresh } = useApi<{ alerts: Alert[]; total: number }>('/alerts')

  const alerts = computed(() => alertsData.value?.alerts ?? MOCK_ALERTS)
  const fraudPatterns = FRAUD_PATTERNS

  const selectedIds = ref<Set<string>>(new Set())
  const selectedAlert = ref<Alert | null>(null)
  const showDetail = ref(false)
  const bulkLoading = ref(false)
  const lockdownLoading = ref(false)
  const lockdownResult = ref<LockdownResult | null>(null)
  const cardCheckCache = ref<Record<string, CardCheckEntry>>({})
  const cardCheckLoading = ref(false)

  const escalationCount = computed(() => alerts.value.filter(a => a.type === 'escalation').length)
  const blockCount = computed(() => alerts.value.filter(a => a.type === 'block').length)
  const unreadCount = computed(() => alerts.value.filter(a => !a.read).length)

  function riskColor(score: number): string {
    if (score >= 80) return 'text-red-600 bg-red-50'
    if (score >= 50) return 'text-amber-600 bg-amber-50'
    return 'text-green-600 bg-green-50'
  }

  function typeBadge(type: string): string {
    return type === 'block' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
  }

  function relativeTime(ts: string): string {
    const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return formatDate(ts, 'MMM dd')
  }

  function toggleSelect(id: string): void {
    if (selectedIds.value.has(id)) selectedIds.value.delete(id)
    else selectedIds.value.add(id)
  }

  function toggleAll(): void {
    if (selectedIds.value.size === alerts.value.length) selectedIds.value.clear()
    else selectedIds.value = new Set(alerts.value.map(a => a.id))
  }

  async function fetchCardCheck(accountId: string): Promise<void> {
    if (cardCheckCache.value[accountId]) return
    cardCheckLoading.value = true
    try {
      const result = await $fetch<{ shared: boolean; linked_count: number; linked_accounts?: LinkedAccount[] }>(
        `/api/alerts/card-check/${accountId}`,
      )
      cardCheckCache.value[accountId] = { ...result, linked_accounts: result.linked_accounts ?? [] }
    }
    catch {
      cardCheckCache.value[accountId] = { shared: false, linked_count: 0, linked_accounts: [] }
    }
    finally {
      cardCheckLoading.value = false
    }
  }

  async function openDetail(alert: Alert): Promise<void> {
    selectedAlert.value = alert
    showDetail.value = true
    lockdownResult.value = null
    await fetchCardCheck(alert.account_id)
  }

  async function bulkAction(action: string): Promise<void> {
    if (selectedIds.value.size === 0) return
    bulkLoading.value = true
    try {
      await $fetch('/api/alerts/bulk-action', { method: 'POST', body: { alert_ids: Array.from(selectedIds.value), action } })
      selectedIds.value.clear()
      await refresh()
    }
    finally {
      bulkLoading.value = false
    }
  }

  async function triggerCardLockdown(): Promise<void> {
    if (!selectedAlert.value) return
    const accountId = selectedAlert.value.account_id
    lockdownLoading.value = true
    try {
      const result = await $fetch<LockdownResult>('/api/alerts/card-lockdown', {
        method: 'POST',
        body: { customer_id: accountId, risk_score: selectedAlert.value.risk_score / 100 },
      })
      lockdownResult.value = result
      delete cardCheckCache.value[accountId]
      await fetchCardCheck(accountId)
      await refresh()
    }
    catch {
      lockdownResult.value = { affected_count: 0, affected_customers: [], affected_accounts: [] }
    }
    finally {
      lockdownLoading.value = false
    }
  }

  function hasSharedCard(alert: Alert): boolean {
    return cardCheckCache.value[alert.account_id]?.shared ?? false
  }

  function linkedAccounts(alert: Alert): LinkedAccount[] {
    return cardCheckCache.value[alert.account_id]?.linked_accounts ?? []
  }

  function allLinkedLocked(alert: Alert): boolean {
    const linked = linkedAccounts(alert)
    return linked.length > 0 && linked.every(a => a.is_locked)
  }

  watch(alerts, (list) => {
    for (const a of list) {
      if (!(a.account_id in cardCheckCache.value)) fetchCardCheck(a.account_id)
    }
  }, { immediate: true })

  return {
    alerts,
    fraudPatterns,
    selectedIds,
    selectedAlert,
    showDetail,
    bulkLoading,
    lockdownLoading,
    lockdownResult,
    cardCheckCache,
    cardCheckLoading,
    escalationCount,
    blockCount,
    unreadCount,
    riskColor,
    typeBadge,
    relativeTime,
    toggleSelect,
    toggleAll,
    openDetail,
    bulkAction,
    triggerCardLockdown,
    hasSharedCard,
    linkedAccounts,
    allLinkedLocked,
  }
}
