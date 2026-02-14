# API Reference -- Pre-Fraud Posture Engine V1

All endpoints are under the `/api` prefix. Tagged as `prefraud` in OpenAPI docs.

**Source files:**
- Routes: `app/api/routes/prefraud.py`
- Schemas: `app/api/schemas/posture.py`

---

## GET /api/customers/{customer_id}/risk-posture

Returns the current risk posture for a customer.

### Parameters

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `customer_id` | path | UUID | yes | Customer UUID |

### Response 200

```json
{
    "customer_id": "606db456-03d1-560b-b807-605e8a36e488",
    "posture": "watch",
    "composite_score": 0.5134,
    "signal_scores": {
        "account_maturity": 0.7246,
        "velocity_trends": 0.7034,
        "infrastructure_stability": 0.3265,
        "funding_behavior": 0.7000,
        "payment_risk": 0.2566,
        "graph_proximity": 0.3750
    },
    "top_reasons": [
        "Account is 9 days old; limited trading (1 trades)",
        "Activity with no prior baseline (new pattern)",
        "Deposit-to-trade ratio extremely high"
    ],
    "trigger": "validation",
    "computed_at": "2026-02-12T06:21:24.756598Z"
}
```

### Response 404

```json
{
    "detail": "No posture computed yet for customer 606db456-03d1-560b-b807-605e8a36e488"
}
```

---

## POST /api/customers/{customer_id}/risk-posture/recompute

Triggers synchronous posture recompute and returns the new snapshot. Uses `trigger="manual"`.

### Parameters

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `customer_id` | path | UUID | yes | Customer UUID |

### Response 200

Same schema as GET endpoint above, with `"trigger": "manual"`.

### Response 500

```json
{
    "detail": "Posture recompute failed: <error message>"
}
```

### Debounce Behavior

If the customer's last posture was computed less than `POSTURE_DEBOUNCE_S` seconds ago (default 5s), the existing posture is returned without recomputing.

---

## GET /api/customers/{customer_id}/risk-posture/history

Returns paginated posture snapshot history for a customer, most recent first.

### Parameters

| Name | In | Type | Required | Default | Description |
|---|---|---|---|---|---|
| `customer_id` | path | UUID | yes | -- | Customer UUID |
| `limit` | query | int | no | 20 | Max snapshots to return (1-100) |
| `offset` | query | int | no | 0 | Number of snapshots to skip |

### Response 200

```json
{
    "customer_id": "606db456-03d1-560b-b807-605e8a36e488",
    "total": 5,
    "snapshots": [
        {
            "posture": "watch",
            "composite_score": 0.5134,
            "signal_scores": { ... },
            "top_reasons": [ ... ],
            "trigger": "manual",
            "computed_at": "2026-02-12T07:00:00Z"
        },
        {
            "posture": "normal",
            "composite_score": 0.2800,
            "signal_scores": { ... },
            "top_reasons": [ ... ],
            "trigger": "scheduled",
            "computed_at": "2026-02-12T06:00:00Z"
        }
    ]
}
```

---

## POST /api/prefraud/recompute-all

Triggers bulk posture recompute for all active customers. Returns a summary with posture distribution and elapsed time.

### Parameters

None.

### Response 200

```json
{
    "total_customers": 16,
    "results": {
        "normal": 10,
        "watch": 4,
        "high_risk": 2
    },
    "elapsed_s": 2.19
}
```

---

## Event-Driven Triggers

In addition to the API endpoints, posture is automatically recomputed via fire-and-forget async tasks at 5 trigger points:

| Event | Trigger String | Code Path |
|---|---|---|
| New device seen | `event:new_device` | Device creation during withdrawal or seed |
| New payment method added | `event:new_method` | PaymentMethod creation |
| New IP or VPN detected | `event:new_ip` | IPHistory creation |
| Withdrawal submitted | `event:withdrawal_request` | `POST /api/payout/investigate` |
| Failed transaction | `event:failed_tx` | Transaction with `status=failed` |

These triggers do NOT block the calling operation. The investigation pipeline reads the **last completed** posture snapshot.

---

## Pydantic Schema Reference

### PostureResponse

```python
class PostureResponse(BaseModel):
    customer_id: uuid.UUID
    posture: Literal["normal", "watch", "high_risk"]
    composite_score: float  # 0.0-1.0
    signal_scores: dict[str, float]
    top_reasons: list[str]
    trigger: str
    computed_at: datetime
```

### PostureSnapshotResponse

```python
class PostureSnapshotResponse(BaseModel):
    posture: Literal["normal", "watch", "high_risk"]
    composite_score: float  # 0.0-1.0
    signal_scores: dict[str, float]
    top_reasons: list[str]
    trigger: str
    computed_at: datetime
```

### PostureHistoryResponse

```python
class PostureHistoryResponse(BaseModel):
    customer_id: uuid.UUID
    total: int
    snapshots: list[PostureSnapshotResponse]
```

### RecomputeAllResult

```python
class RecomputeAllResult(BaseModel):
    total_customers: int
    results: dict[str, int]  # {"normal": N, "watch": N, "high_risk": N}
    elapsed_s: float
```
