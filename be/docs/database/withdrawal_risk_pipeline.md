# ER Diagram: Withdrawal Risk Pipeline

This view focuses on the core fraud-evaluation flow for withdrawals.

```mermaid
erDiagram
    CUSTOMERS {
        uuid id PK
        string external_id UK
    }

    PAYMENT_METHODS {
        uuid id PK
        uuid customer_id FK
        string type
    }

    WITHDRAWALS {
        uuid id PK
        uuid customer_id FK
        uuid payment_method_id FK
        decimal amount
        string currency
        string status
        datetime requested_at
    }

    EVALUATIONS {
        uuid id PK
        uuid withdrawal_id FK
        decimal composite_score
        string decision
        string risk_level
        datetime checked_at
    }

    INDICATOR_RESULTS {
        uuid id PK
        uuid withdrawal_id FK
        uuid evaluation_id FK
        string indicator_name
        decimal score
        decimal weight
        decimal confidence
    }

    WITHDRAWAL_DECISIONS {
        uuid id PK
        uuid withdrawal_id FK
        uuid evaluation_id FK
        string decision
        decimal composite_score
        datetime decided_at
    }

    CUSTOMERS ||--o{ WITHDRAWALS : requests
    PAYMENT_METHODS ||--o{ WITHDRAWALS : receives_to
    WITHDRAWALS ||--o{ EVALUATIONS : rechecked_by
    WITHDRAWALS ||--o{ INDICATOR_RESULTS : produces
    EVALUATIONS o|--o{ INDICATOR_RESULTS : optional_eval_link
    WITHDRAWALS ||--|| WITHDRAWAL_DECISIONS : final_fraud_decision
    EVALUATIONS o|--o{ WITHDRAWAL_DECISIONS : optional_source
```

Notes:

- `withdrawal_decisions.withdrawal_id` is unique, so each withdrawal has at most one final decision row.
- `indicator_results` keeps both `withdrawal_id` and optional `evaluation_id` to support old and new pipeline linkage.
- `withdrawals.status` is workflow state, while `withdrawal_decisions.decision` is the fraud decision of record.
- For service-level write flow (`_persist`) and rule-vs-LLM storage split, see `investigator_service_persistence.md`.
