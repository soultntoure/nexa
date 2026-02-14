# Card Lockdown — Workflow

How officers detect and lock down shared cards across accounts.

---

## High-Level Flow

```mermaid
flowchart LR
    A[Officer views alerts] -->|sees shared card badge| B[Opens alert detail]
    B -->|clicks Card Lockdown| C[Backend executes lockdown]
    C --> D[Linked accounts flagged]
    C --> E[Shared cards blacklisted]
    C --> F[New alerts generated]
    D & E & F --> G[Officer sees result banner]
```

---

## Officer Walkthrough

```mermaid
sequenceDiagram
    participant Officer
    participant Alerts as /alerts page
    participant Modal as Alert Detail Modal
    participant API as Backend API
    participant DB as PostgreSQL

    Note over Officer,DB: STEP 1 — Detect shared card

    Officer->>Alerts: Opens /alerts page
    Alerts->>API: GET /api/alerts/card-check/{external_id} (per alert)
    API-->>Alerts: {shared: true, linked_count: 2}
    Alerts->>Alerts: Show orange "Shared card (2)" badge

    Note over Officer,DB: STEP 2 — Review and execute

    Officer->>Alerts: Clicks alert row
    Alerts->>Modal: Open detail modal
    Modal->>Modal: Show "Card Lockdown" button (orange, active)

    Officer->>Modal: Clicks "Card Lockdown"
    Modal->>API: POST /api/alerts/card-lockdown {customer_id, risk_score}

    API->>DB: Find linked payment methods (same last_four + provider)
    API->>DB: Flag linked customers (is_flagged = true)
    API->>DB: Blacklist shared cards (is_blacklisted = true)
    API->>DB: Create card_lockdown alerts per linked customer
    API->>DB: COMMIT (atomic)

    API-->>Modal: {affected_customers: ["CUST-007", "CUST-009"], affected_count: 2}
    Modal->>Modal: Show result banner

    Note over Officer,DB: STEP 3 — Aftermath

    Alerts->>API: GET /api/alerts (refresh)
    API-->>Alerts: New card_lockdown alerts appear

    Officer->>Officer: Navigate to /customers
    Note over Officer: CUST-007 and CUST-009 show red "Flagged" badge
```

---

## Card Check Flow (Badge Detection)

```mermaid
flowchart TD
    MOUNT[Alerts page mounts] --> FETCH["For each visible alert:<br/>GET /api/alerts/card-check/{id}"]

    FETCH --> CHECK{shared == true?}
    CHECK -->|Yes| BADGE["Show orange badge:<br/>Shared card (N)"]
    CHECK -->|No| NONE[No badge]

    BADGE --> CACHE[Cache result in cardCheckCache]
    NONE --> CACHE

    CLICK[Officer clicks alert row] --> MODAL[Open detail modal]
    MODAL --> CACHED{In cache?}
    CACHED -->|Yes| BUTTON{shared?}
    CACHED -->|No| REFETCH[Fetch card-check again]
    REFETCH --> BUTTON

    BUTTON -->|true| ACTIVE["Card Lockdown button: orange, active"]
    BUTTON -->|false| DISABLED["Card Lockdown button: grayed, disabled"]
```

---

## Lockdown Execution (Atomic Transaction)

```mermaid
flowchart TD
    REQ[POST /card-lockdown] --> RESOLVE[Resolve customer by external_id]
    RESOLVE --> CARD[Get latest card by last_used_at]
    CARD --> WD[Get latest withdrawal]
    WD --> LINKED[Find linked payment methods<br/>same last_four + provider, different customer]

    LINKED --> CHECK{Any linked found?}
    CHECK -->|No| EMPTY[Return: 0 affected]
    CHECK -->|Yes| TX[Begin transaction]

    TX --> FLAG[Flag linked customers<br/>is_flagged = true<br/>flag_reason = 'Card lockdown: shared card']
    FLAG --> BLACK[Blacklist all shared cards<br/>is_blacklisted = true]
    BLACK --> ALERTS[Create card_lockdown alert<br/>per linked customer]
    ALERTS --> COMMIT[COMMIT]

    COMMIT --> RESULT["Return: affected_customers, count, blacklisted_methods"]

    TX -.->|Any error| ROLLBACK[ROLLBACK — no partial state]
    ROLLBACK -.-> ERROR["Return: error message"]

    classDef success fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef error fill:#E74C3C,stroke:#333,stroke-width:2px,color:#000
    class COMMIT,RESULT success
    class ROLLBACK,ERROR error
```

---

## Notification Flow

```mermaid
sequenceDiagram
    participant Bell as NotificationDropdown
    participant API as /api/alerts

    loop Every 30 seconds
        Bell->>API: GET /api/alerts
        API-->>Bell: Alert list (includes card_lockdown type)
        Bell->>Bell: Filter for card_lockdown alerts
        Bell->>Bell: Show orange credit-card icon
    end
```

---

## Post-Lockdown State

```mermaid
flowchart LR
    subgraph Before Lockdown
        C1[CUST-007: normal]
        C2[CUST-009: normal]
        PM1[Visa-4242: active]
        PM2[Visa-4242: active]
    end

    subgraph After Lockdown
        C3[CUST-007: flagged]
        C4[CUST-009: flagged]
        PM3[Visa-4242: blacklisted]
        PM4[Visa-4242: blacklisted]
        A1[Alert: card_lockdown for CUST-007]
        A2[Alert: card_lockdown for CUST-009]
    end

    C1 --> C3
    C2 --> C4
    PM1 --> PM3
    PM2 --> PM4
```
