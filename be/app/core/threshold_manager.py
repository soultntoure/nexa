"""
Read/adjust thresholds from DB.

Contains:
- ThresholdManager class
  - get_current_thresholds() -> ThresholdConfig
  - update_thresholds(adjustments: dict) -> ThresholdConfig
  - recalculate_from_feedback(feedback_stats: dict) -> ThresholdConfig

- ThresholdConfig dataclass:
  - approve_below: float (default 30)
  - escalate_below: float (default 70)
  - indicator_weights: dict[str, float]
  - last_updated: datetime

Reads from threshold_config table in Postgres.
No model retraining — just numeric boundary adjustments.
"""
