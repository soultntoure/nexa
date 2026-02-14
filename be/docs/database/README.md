# Database Schema ER Docs

This folder splits the schema into smaller ER diagrams so each view is easy to scan.

The diagrams intentionally show only key columns (PK/FK plus a few important fields).

## Documents

| # | File | Tables Covered |
|---|------|---------------|
| 1 | [customer_and_activity.md](customer_and_activity.md) | customers, payment_methods, transactions, trades, devices, ip_history |
| 2 | [withdrawal_risk_pipeline.md](withdrawal_risk_pipeline.md) | withdrawals, evaluations, indicator_results, withdrawal_decisions |
| 3 | [review_feedback_alerts.md](review_feedback_alerts.md) | alerts, feedback |
| 4 | [config_and_learning.md](config_and_learning.md) | customer_weight_profiles, fraud_patterns, threshold_config |
| 5 | [investigator_service_persistence.md](investigator_service_persistence.md) | evaluations.investigation_data JSONB, persistence sequence |

## Mermaid relationship legend

- `||--||`: one-to-one
- `||--o{`: one-to-many
- `o|--o{`: zero-or-one to many
