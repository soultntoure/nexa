# ER Diagram: Customer and Activity

This view focuses on customer profile data and account activity tables.

```mermaid
erDiagram
    CUSTOMERS {
        uuid id PK
        string external_id UK
        string email UK
        string country
        boolean is_flagged
    }

    PAYMENT_METHODS {
        uuid id PK
        uuid customer_id FK
        string type
        string provider
        boolean is_verified
        boolean is_blacklisted
    }

    TRANSACTIONS {
        uuid id PK
        uuid customer_id FK
        uuid payment_method_id FK
        string type
        decimal amount
        string status
        datetime timestamp
    }

    TRADES {
        uuid id PK
        uuid customer_id FK
        string instrument
        decimal amount
        decimal pnl
        datetime opened_at
    }

    DEVICES {
        uuid id PK
        uuid customer_id FK
        string fingerprint
        boolean is_trusted
        datetime first_seen_at
        datetime last_seen_at
    }

    IP_HISTORY {
        uuid id PK
        uuid customer_id FK
        string ip_address
        string location
        boolean is_vpn
        datetime last_seen_at
    }

    CUSTOMERS ||--o{ PAYMENT_METHODS : owns
    CUSTOMERS ||--o{ TRANSACTIONS : makes
    CUSTOMERS ||--o{ TRADES : places
    CUSTOMERS ||--o{ DEVICES : uses
    CUSTOMERS ||--o{ IP_HISTORY : appears_from
    PAYMENT_METHODS o|--o{ TRANSACTIONS : optional_method
```

Notes:

- `transactions.payment_method_id` is nullable, so not every transaction is tied to a saved method.
- `customers.external_id` is the API-facing identifier (for example `CUST-001`).
