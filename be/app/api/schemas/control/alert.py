"""
Pydantic models for alert endpoints.

Contains:
- AlertItem: alert_id, withdrawal_id, customer_id, alert_type (block/escalation),
  risk_score, top_indicators, summary, is_read, created_at
- AlertListResponse: total, items (list[AlertItem])
- BulkActionRequest: action (freeze_withdrawals/lock_accounts/dismiss),
  customer_ids (list[str]), reason
- BulkActionResponse: action, affected_customer_ids, affected_count,
  performed_by, performed_at, status
"""
