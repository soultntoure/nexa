# Card Lockdown — Data Model

Database tables, match criteria, and seed data for the card lockdown feature.

---

## Tables Involved

```mermaid
erDiagram
    customers ||--o{ payment_methods : has
    customers ||--o{ withdrawals : makes
    customers ||--o{ alerts : receives
    withdrawals ||--o{ alerts : triggers
    payment_methods ||--o{ withdrawals : used_in

    customers {
        UUID id PK
        VARCHAR external_id
        BOOLEAN is_flagged
        TEXT flag_reason
    }

    payment_methods {
        UUID id PK
        UUID customer_id FK
        VARCHAR last_four
        VARCHAR provider
        VARCHAR type
        BOOLEAN is_blacklisted
        BOOLEAN is_verified
        TIMESTAMP added_at
        TIMESTAMP last_used_at
    }

    alerts {
        UUID id PK
        UUID withdrawal_id FK
        UUID customer_id FK
        VARCHAR alert_type
        FLOAT risk_score
        JSONB top_indicators
    }

    withdrawals {
        UUID id PK
        UUID customer_id FK
        UUID payment_method_id FK
        TIMESTAMP requested_at
    }
```

---

## Card Match Criteria

```mermaid
flowchart LR
    SOURCE[Source card:<br/>Visa-4242] --> MATCH{"last_four = '4242'<br/>AND provider = 'visa'<br/>AND customer_id != source"}
    MATCH -->|Match| LINKED[Linked cards<br/>on other accounts]
    MATCH -->|No match| NONE[No linked accounts]
```

| Decision | Rationale |
|----------|-----------|
| Match on `last_four` + `provider` | Same card across accounts |
| Not just `last_four` | Different providers can share last 4 digits |
| Not full PAN | PCI compliance — only last 4 stored |
| Exclude source customer | Source is already blocked/escalated |

---

## What Gets Modified

```mermaid
flowchart TD
    LOCKDOWN[Card Lockdown Executes] --> FLAG["customers:<br/>is_flagged = true<br/>flag_reason = 'Card lockdown: shared card'"]
    LOCKDOWN --> BLACK["payment_methods:<br/>is_blacklisted = true"]
    LOCKDOWN --> ALERT["alerts:<br/>INSERT (type='card_lockdown',<br/>risk_score, top_indicators)"]

    FLAG --> FUTURE_CUST["/customers page:<br/>red Flagged badge"]
    BLACK --> FUTURE_TX["Future transactions:<br/>card rejected"]
    ALERT --> FUTURE_ALERT["/alerts page:<br/>new card_lockdown alerts"]
```

---

## Seed Data: Shared Card Pairs

3 pairs of fraud-tier customers share the same card:

| Pair | Customer A | Customer B | Shared Card | Fraud Type |
|------|-----------|-----------|-------------|------------|
| 1 | CUST-011 (Victor) | CUST-012 (Sophie) | Visa-1111 | Device sharing + card testing |
| 2 | CUST-013 (Ahmed) | CUST-014 (Fatima) | Visa-4444 | Fraud ring (device + IP + recipient + card) |
| 3 | CUST-015 (Carlos) | CUST-016 (Nina) | Visa-6677 | Velocity abuse + impossible travel |

All 6 customers have pending withdrawals with `is_fraud=True`.

### Verify After Seeding

```sql
-- Should show 3 rows with count=2 each
SELECT last_four, provider, COUNT(DISTINCT customer_id) AS customers
FROM payment_methods
WHERE last_four IS NOT NULL
GROUP BY last_four, provider
HAVING COUNT(DISTINCT customer_id) > 1;
```

---

## Audit Trail

| What | Where | Immutable? |
|------|-------|------------|
| Flagged customers | `customers.is_flagged` + `flag_reason` | flag_reason not modified after lockdown |
| Blacklisted cards | `payment_methods.is_blacklisted` | Append-only state change |
| Generated alerts | `alerts` table (type = `card_lockdown`) | Append-only, never deleted |
| Original withdrawal | `alerts.withdrawal_id` FK | Links back to triggering event |

---

## Security

| Concern | Mitigation |
|---------|-----------|
| PCI compliance | Only `last_four` + `provider` stored and matched |
| Partial state | Atomic transaction — all-or-nothing commit |
| Audit immutability | Alerts append-only, flag_reason immutable |
| Authorization | Demo mode (no auth). Production: restrict POST to compliance officers |
