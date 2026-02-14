# ER Diagram: Config and Learning Tables

This view covers dynamic scoring configuration and pattern-learning data.

```mermaid
erDiagram
    CUSTOMERS {
        uuid id PK
        string external_id UK
    }

    EVALUATIONS {
        uuid id PK
        uuid withdrawal_id FK
        decimal composite_score
        string decision
    }

    CUSTOMER_WEIGHT_PROFILES {
        uuid id PK
        uuid customer_id FK
        jsonb indicator_weights
        jsonb blend_weights
        jsonb decision_window
        boolean is_active
    }

    FRAUD_PATTERNS {
        uuid id PK
        string pattern_type
        jsonb indicator_combination
        decimal confidence
        uuid customer_id FK
        uuid evaluation_id FK
        string signal_type
    }

    THRESHOLD_CONFIG {
        uuid id PK
        decimal approve_below
        decimal escalate_below
        jsonb indicator_weights
        boolean is_active
        string updated_by
    }

    CUSTOMERS ||--o{ CUSTOMER_WEIGHT_PROFILES : has_profiles
    CUSTOMERS o|--o{ FRAUD_PATTERNS : optional_anchor
    EVALUATIONS o|--o{ FRAUD_PATTERNS : optional_anchor
```

Notes:

- `threshold_config` has no FK links; it is a versioned global config table.
- `customer_weight_profiles` supports per-customer personalization over time.
- `fraud_patterns` can optionally point to either a customer, an evaluation, or both.
