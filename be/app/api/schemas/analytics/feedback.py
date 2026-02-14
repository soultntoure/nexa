"""
Pydantic models for dashboard endpoint.

Contains:
- DashboardStats: period, total_withdrawals, decisions (approved/escalated/blocked),
  accuracy (total_reviewed, correct, incorrect, accuracy_rate),
  top_risk_indicators, alert_summary, threshold_config
- RiskIndicatorStat: name, avg_score, trigger_count
- AlertSummary: total_active, unread, blocks_today, escalations_today
- ThresholdInfo: approve_below, escalate_below, last_updated, updated_by
"""
