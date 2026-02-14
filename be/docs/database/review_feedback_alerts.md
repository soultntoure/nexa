# ER Diagram: Review, Feedback, and Alerts

This view focuses on operational review artifacts around a withdrawal.

```mermaid
erDiagram
    CUSTOMERS {
        uuid id PK
        string external_id UK
    }

    WITHDRAWALS {
        uuid id PK
        uuid customer_id FK
        decimal amount
        string status
        datetime requested_at
    }

    ALERTS {
        uuid id PK
        uuid withdrawal_id FK
        uuid customer_id FK
        string alert_type
        decimal risk_score
        boolean is_read
        datetime created_at
    }

    FEEDBACK {
        uuid id PK
        uuid withdrawal_id FK
        string admin_id
        boolean is_correct
        datetime created_at
    }

    CUSTOMERS ||--o{ WITHDRAWALS : owns
    CUSTOMERS ||--o{ ALERTS : receives
    WITHDRAWALS ||--o{ ALERTS : triggers
    WITHDRAWALS ||--o{ FEEDBACK : reviewed_with
```

Notes:

- `alerts.top_indicators` stores a compact JSONB explanation payload.
- `feedback` is used to track whether system decisions were correct after human review.
