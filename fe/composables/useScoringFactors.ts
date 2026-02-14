export interface IndicatorRow {
  name: string
  baseline_weight: number
  customer_multiplier: number
  customer_weight: number
  difference: number
  status: string
  reason: string
}

export interface WeightSnapshot {
  customer_id: string
  personalization_status: string
  last_updated: string | null
  sample_count: number
  blend: {
    baseline: { rule_engine: number; investigators: number }
    customer: { rule_engine: number; investigators: number }
  }
  indicators: IndicatorRow[]
}

export interface AgentSignal {
  name: string
  multiplier: number
  direction: string
  pct: number
  reason: string
}

// Mirror backend thresholds from weight_context.py
const BOOSTED_THRESHOLD = 1.15
const DAMPENED_THRESHOLD = 0.85
const WATCHLIST_DELTA = 0.08

export const INDICATOR_LABELS: Record<string, string> = {
  trading_behavior: 'Trading Behavior',
  device_fingerprint: 'Device Fingerprint',
  geographic: 'Geographic Signals',
  amount_anomaly: 'Amount Anomaly',
  velocity: 'Transaction Velocity',
  payment_method: 'Payment Method',
  recipient: 'Recipient Analysis',
  card_errors: 'Card Error History',
}

export const INDICATOR_ICONS: Record<string, string> = {
  trading_behavior: 'lucide:trending-up',
  device_fingerprint: 'lucide:fingerprint',
  geographic: 'lucide:map-pin',
  amount_anomaly: 'lucide:circle-dollar-sign',
  velocity: 'lucide:zap',
  payment_method: 'lucide:credit-card',
  recipient: 'lucide:users',
  card_errors: 'lucide:alert-triangle',
}

export const STATUS_BADGE: Record<string, { bg: string; text: string }> = {
  stable: { bg: 'bg-green-100', text: 'text-green-700' },
  'limited data': { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  'baseline fallback': { bg: 'bg-gray-100', text: 'text-gray-600' },
}

export function multiplierLabel(mult: number): string {
  const pct = Math.round((mult - 1) * 100)
  if (pct === 0) return 'Baseline'
  return pct > 0 ? `+${pct}%` : `${pct}%`
}

export function multiplierStyle(mult: number): string {
  if (mult > BOOSTED_THRESHOLD) return 'text-red-600 bg-red-50'
  if (mult < DAMPENED_THRESHOLD) return 'text-green-600 bg-green-50'
  if (mult !== 1.0) return 'text-yellow-600 bg-yellow-50'
  return 'text-gray-500 bg-gray-50'
}

export function multiplierIcon(mult: number): string {
  if (mult > BOOSTED_THRESHOLD) return 'lucide:chevron-up'
  if (mult < DAMPENED_THRESHOLD) return 'lucide:chevron-down'
  return 'lucide:minus'
}

function classifySignals(indicators: IndicatorRow[], category: 'boosted' | 'dampened' | 'emerging'): AgentSignal[] {
  return indicators
    .filter((r) => {
      const m = r.customer_multiplier
      if (category === 'boosted') return m > BOOSTED_THRESHOLD
      if (category === 'dampened') return m < DAMPENED_THRESHOLD
      return m >= DAMPENED_THRESHOLD && m <= BOOSTED_THRESHOLD && Math.abs(m - 1.0) >= WATCHLIST_DELTA
    })
    .map(r => ({
      name: r.name,
      multiplier: r.customer_multiplier,
      direction: r.customer_multiplier > 1 ? 'upweighted' : 'downweighted',
      pct: Math.abs(Math.round((r.customer_multiplier - 1) * 100)),
      reason: r.reason,
    }))
    .sort((a, b) => Math.abs(b.multiplier - 1) - Math.abs(a.multiplier - 1))
}

export function useScoringFactors(customerId: Ref<string>) {
  const snapshot = ref<WeightSnapshot | null>(null)
  const loading = ref(false)
  const error = ref('')
  const resetting = ref(false)

  async function fetchSnapshot() {
    loading.value = true
    error.value = ''
    try {
      snapshot.value = await $fetch<WeightSnapshot>(`/api/customers/${customerId.value}/weights`)
    }
    catch { error.value = 'Could not load scoring factors.' }
    finally { loading.value = false }
  }

  async function resetToBaseline() {
    if (!confirm('Reset this customer to baseline weights?')) return
    resetting.value = true
    try {
      await $fetch(`/api/customers/${customerId.value}/weights/reset`, {
        method: 'POST',
        body: { reason: 'Manual reset by officer', updated_by: 'officer-demo-001' },
      })
      await fetchSnapshot()
    }
    catch { error.value = 'Reset failed.' }
    finally { resetting.value = false }
  }

  const adjustedIndicators = computed(() =>
    snapshot.value?.indicators.filter(r => Math.abs(r.customer_multiplier - 1.0) > 0.01) ?? [],
  )
  const baselineIndicators = computed(() =>
    snapshot.value?.indicators.filter(r => Math.abs(r.customer_multiplier - 1.0) <= 0.01) ?? [],
  )
  const blendChanged = computed(() => {
    if (!snapshot.value) return false
    return Math.abs(snapshot.value.blend.baseline.rule_engine - snapshot.value.blend.customer.rule_engine) > 0.01
  })
  const isPersonalized = computed(() =>
    snapshot.value?.personalization_status === 'applied'
    || snapshot.value?.personalization_status === 'limited data',
  )

  const boostedSignals = computed(() => classifySignals(snapshot.value?.indicators ?? [], 'boosted'))
  const dampenedSignals = computed(() => classifySignals(snapshot.value?.indicators ?? [], 'dampened'))
  const emergingSignals = computed(() => classifySignals(snapshot.value?.indicators ?? [], 'emerging'))
  const hasAgentGuidance = computed(() =>
    boostedSignals.value.length > 0 || dampenedSignals.value.length > 0 || emergingSignals.value.length > 0,
  )

  return {
    snapshot, loading, error, resetting,
    fetchSnapshot, resetToBaseline,
    adjustedIndicators, baselineIndicators,
    blendChanged, isPersonalized,
    boostedSignals, dampenedSignals, emergingSignals, hasAgentGuidance,
  }
}
