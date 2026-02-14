# Card Lockdown — Backend Architecture

Vertical slice: route → service → repository → database.

---

## Layer Diagram

```mermaid
flowchart TD
    subgraph API["API Layer"]
        R1["GET /api/alerts/card-check/{id}"]
        R2["POST /api/alerts/card-lockdown"]
    end

    subgraph Service["Service Layer"]
        CHECK[check_shared_card]
        EXEC[execute_card_lockdown_by_customer]
        LOCK[_execute_lockdown]
    end

    subgraph Repo["Repository Layer"]
        FIND_CARD[find_latest_card]
        FIND_LINKED[find_linked_by_card]
    end

    subgraph DB["PostgreSQL"]
        PM[(payment_methods)]
        CUST[(customers)]
        ALERTS[(alerts)]
        WD[(withdrawals)]
    end

    R1 --> CHECK
    R2 --> EXEC
    EXEC --> LOCK

    CHECK --> FIND_CARD --> PM
    CHECK --> FIND_LINKED --> PM
    LOCK --> FIND_LINKED
    LOCK --> CUST
    LOCK --> PM
    LOCK --> ALERTS
    LOCK --> WD

    classDef api fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef svc fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef repo fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000
    classDef db fill:#9B59B6,stroke:#333,stroke-width:2px,color:#000

    class R1,R2 api
    class CHECK,EXEC,LOCK svc
    class FIND_CARD,FIND_LINKED repo
    class PM,CUST,ALERTS,WD db
```

---

## Card Check (Read-Only)

```mermaid
sequenceDiagram
    participant API as GET /card-check/{id}
    participant SVC as check_shared_card()
    participant Repo as PaymentMethodRepository
    participant DB as PostgreSQL

    API->>SVC: check_shared_card(session, external_id)
    SVC->>DB: SELECT * FROM customers WHERE external_id = ?
    DB-->>SVC: Customer(id, ...)

    SVC->>Repo: find_latest_card(customer_id)
    Repo->>DB: SELECT * FROM payment_methods<br/>WHERE customer_id = ? AND type = 'card'<br/>ORDER BY last_used_at DESC LIMIT 1
    DB-->>Repo: PaymentMethod(id, last_four, provider)

    SVC->>Repo: find_linked_by_card(payment_method_id, customer_id)
    Repo->>DB: SELECT * FROM payment_methods<br/>WHERE last_four = ? AND provider = ?<br/>AND customer_id != ?
    DB-->>Repo: [PaymentMethod, ...]

    SVC->>SVC: Count unique customer_ids from linked methods
    SVC-->>API: {shared: true, linked_count: 2}
```

---

## Lockdown Execution (Write Transaction)

```mermaid
sequenceDiagram
    participant API as POST /card-lockdown
    participant SVC as execute_card_lockdown_by_customer()
    participant LOCK as _execute_lockdown()
    participant Repo as PaymentMethodRepository
    participant DB as PostgreSQL

    API->>SVC: execute_card_lockdown_by_customer(session, external_id, risk_score)
    SVC->>SVC: _resolve_customer(external_id)
    SVC->>SVC: _get_latest_card(customer_id)
    SVC->>SVC: _get_latest_withdrawal(customer_id)

    SVC->>LOCK: _execute_lockdown(session, payment_method_id, customer_id, withdrawal_id, risk_score)

    LOCK->>Repo: find_linked_by_card(payment_method_id, customer_id)
    Repo-->>LOCK: [linked_method_1, linked_method_2]

    LOCK->>DB: UPDATE customers SET is_flagged=true<br/>WHERE id IN (linked_customer_ids)
    LOCK->>DB: UPDATE payment_methods SET is_blacklisted=true<br/>WHERE id IN (all_shared_method_ids)
    LOCK->>DB: INSERT INTO alerts (type='card_lockdown')<br/>FOR EACH linked customer
    LOCK->>DB: COMMIT

    LOCK-->>SVC: {affected_customers, affected_count, blacklisted_methods}
    SVC-->>API: Response
```

---

## Service Functions

| Function | File | Purpose |
|----------|------|---------|
| `check_shared_card()` | `card_lockdown_service.py:22` | Read-only: count linked accounts |
| `execute_card_lockdown_by_customer()` | `card_lockdown_service.py:40` | Entry point: resolve IDs, delegate to lockdown |
| `_resolve_customer()` | `card_lockdown_service.py:67` | Lookup by external_id |
| `_get_latest_card()` | `card_lockdown_service.py` | Most recently used card (type='card', has last_four) |
| `_get_latest_withdrawal()` | `card_lockdown_service.py` | Most recent withdrawal request |
| `_execute_lockdown()` | `card_lockdown_service.py` | Atomic: find linked → flag → blacklist → alert → commit |
| `_flag_customers()` | `card_lockdown_service.py` | UPDATE customers SET is_flagged=true |
| `_blacklist_methods()` | `card_lockdown_service.py` | UPDATE payment_methods SET is_blacklisted=true |
| `_create_alerts()` | `card_lockdown_service.py` | INSERT card_lockdown alerts per linked customer |

## Repository Method

```
find_linked_by_card(payment_method_id, exclude_customer_id) → list[PaymentMethod]
```

| Step | What |
|------|------|
| 1 | Fetch source payment method → extract `last_four` + `provider` |
| 2 | Query all payment methods with matching `last_four` AND `provider` AND different customer |
| 3 | Expunge from session, return detached list |
| 4 | If source has null `last_four` → return empty list (non-card method) |

---

## Error Handling

```mermaid
flowchart TD
    REQ[Request arrives] --> TRY[Try execute lockdown]

    TRY -->|Success| COMMIT[COMMIT + return result]
    TRY -->|Customer not found| ERR1["Return {error: 'Customer not found'}"]
    TRY -->|No card found| ERR2["Return {error: 'No card payment method found'}"]
    TRY -->|No withdrawal found| ERR3["Return {error: 'No withdrawal found'}"]
    TRY -->|SQL error| ROLLBACK[ROLLBACK + log + re-raise RuntimeError]

    ROLLBACK --> ERR4["Route catches → return {affected_count: 0, error: str}"]

    classDef ok fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef err fill:#E74C3C,stroke:#333,stroke-width:2px,color:#000
    class COMMIT ok
    class ERR1,ERR2,ERR3,ERR4,ROLLBACK err
```

- All-or-nothing atomicity — no partial commits
- Route layer catches all exceptions, never exposes stack traces
- Error responses use same schema with `error` field added
