import type { Transaction } from '~/composables/useTransactions'

export interface WithdrawalDiscussionContext {
  id: string
  withdrawal_id: string
  customer_external_id: string
  customer_name: string
  customer_email: string
  amount: number
  currency: string
  risk_score: number
  risk_level: string
  status: string
  payment_method: string
  recipient_name: string
  recipient_account: string
  ip_address: string
  device: string
  created_at: string
}

function toDiscussionContext(tx: Transaction): WithdrawalDiscussionContext {
  return {
    id: tx.id,
    withdrawal_id: tx.withdrawal_id,
    customer_external_id: tx.customer.external_id,
    customer_name: tx.customer.name,
    customer_email: tx.customer.email,
    amount: tx.amount,
    currency: tx.currency,
    risk_score: tx.risk_score,
    risk_level: tx.risk_level,
    status: tx.status,
    payment_method: tx.payment_method,
    recipient_name: tx.recipient.name,
    recipient_account: tx.recipient.account_number,
    ip_address: tx.ip_address,
    device: tx.device,
    created_at: tx.created_at,
  }
}

function buildDiscussionPrompt(ctx: WithdrawalDiscussionContext): string {
  return [
    `Analyze withdrawal ${ctx.withdrawal_id} for ${ctx.customer_name} (${ctx.customer_external_id}).`,
    `Amount: ${ctx.amount} ${ctx.currency}. Risk score: ${ctx.risk_score.toFixed(2)} (${ctx.risk_level}).`,
    `Payment: ${ctx.payment_method}. Recipient: ${ctx.recipient_name} (${ctx.recipient_account}).`,
    `Network context: IP ${ctx.ip_address}, device ${ctx.device}.`,
    'Give me a concise fraud assessment, key red flags, and what I should verify next.',
  ].join(' ')
}

export function useWithdrawalDiscussion() {
  const discussionContext = useState<WithdrawalDiscussionContext | null>(
    'withdrawal-discussion-context',
    () => null,
  )

  function setDiscussionFromTransaction(tx: Transaction) {
    discussionContext.value = toDiscussionContext(tx)
  }

  function clearDiscussionContext() {
    discussionContext.value = null
  }

  return {
    discussionContext,
    setDiscussionFromTransaction,
    clearDiscussionContext,
    buildDiscussionPrompt,
  }
}
