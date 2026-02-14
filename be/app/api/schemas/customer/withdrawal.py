"""
Pydantic models for payout endpoints.

Contains:
- EvaluateRequest: customer_id, amount, currency, payment_method_id,
  recipient_name, recipient_account, ip_address, device_fingerprint, location
- EvaluateResponse: withdrawal_id, decision (approve/escalate/block),
  risk_score (0-100), reasoning, indicator_results (list[IndicatorScore])
- IndicatorScore: name, score (0-1), weight, reasoning
- QueueItem: withdrawal_id, customer_id, amount, risk_score, decision,
  top_indicators, requested_at
- QueueResponse: total, items (list[QueueItem])
- DecisionRequest: withdrawal_id, officer_id, action (approve/block), reason
- DecisionResponse: withdrawal_id, officer_id, action, decided_at, status
"""
