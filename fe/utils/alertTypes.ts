export interface Alert {
  id: string
  type: 'escalation' | 'block' | 'card_lockdown'
  customer_name: string
  account_id: string
  risk_score: number
  indicators: { name: string; score: number }[]
  timestamp: string
  read: boolean
  amount: number
  currency: string
}

export interface LinkedAccount {
  customer_id: string
  customer_name: string
  is_locked?: boolean
}

export interface LockdownResult {
  affected_count: number
  affected_customers: string[]
  affected_accounts?: LinkedAccount[]
}

export interface FraudPattern {
  name: string
  key: string
  accounts_affected: number
  total_exposure: number
  confidence: number
}

export const INDICATOR_LABELS: Record<string, string> = {
  amount_anomaly: 'Amount Anomaly',
  velocity: 'Velocity',
  payment_method: 'Payment Method',
  geographic: 'Geographic',
  device_fingerprint: 'Device Fingerprint',
  trading_behavior: 'Trading Behavior',
  recipient: 'Recipient Risk',
  card_errors: 'Card Errors',
}

export const PATTERN_ICONS: Record<string, string> = {
  no_trade: 'lucide:ban',
  short_trade: 'lucide:timer',
  card_testing: 'lucide:credit-card',
  velocity: 'lucide:gauge',
}
