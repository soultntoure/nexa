# Adaptive Weighting System — Overview

Customer-specific weights that learn from officer decisions. Three things adapt per customer: indicator multipliers, LLM prompt context, and rule/investigator blend ratio.

---

## The Loop

```mermaid
flowchart LR
    A[Investigation] -->|uses profile| B[Officer Reviews]
    B -->|approve/block| C[Feedback Loop]
    C -->|recalibrates| D[Updated Profile]
    D -->|next request| A
```

---

## Investigation: How Weights Are Used

```mermaid
flowchart TD
    REQ[New Investigation] --> LOAD{Active profile?}

    LOAD -->|No| BASE[Baseline weights]
    LOAD -->|Yes| EFF[effective = baseline × multiplier]

    BASE --> INDICATORS[Run 8 Rule Indicators]
    EFF --> INDICATORS

    INDICATORS --> SCORE[Composite Score]
    SCORE --> GATE{Score range?}

    GATE -->|"< 0.30 or >= 0.70"| FAST[Fast path — 0 LLM calls]
    GATE -->|"0.30 – 0.70"| WCTX[Build weight context string]

    WCTX --> TRIAGE[Triage with weight context]
    TRIAGE --> INVEST[Investigators with weight context]
    INVEST --> BLEND[Blend: rule × rule_w + inv × inv_w]

    FAST --> DONE[Return decision]
    BLEND --> DONE

    classDef fast fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef llm fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    class FAST fast
    class TRIAGE,INVEST,WCTX llm
```

---

## Feedback: How Weights Are Updated

```mermaid
sequenceDiagram
    participant Officer as Officer UI
    participant FB as FeedbackLoopService
    participant CAL as Calibration Engine
    participant DB as PostgreSQL

    Officer->>FB: POST /payout/decision (approve or block)

    FB->>DB: Fetch decision window for this customer
    DB-->>FB: Last N decisions + indicator scores

    FB->>CAL: recalculate_profile(decisions, current_profile)

    loop Each indicator
        CAL->>CAL: Officer agreed with rule signal? → reinforce
        CAL->>CAL: Officer overruled rule signal? → adjust
    end

    CAL->>CAL: calculate_blend_weights(decisions)
    CAL->>DB: Save new active profile

    Note over Officer,DB: Next investigation reads updated profile
```

---

## Snapshot API: How Officers See Weights

```mermaid
sequenceDiagram
    participant UI as ScoringFactorsDrawer
    participant API as /api/customers/:id/weights
    participant SVC as CustomerWeightExplainService
    participant DB as PostgreSQL

    UI->>API: GET /api/customers/CUST-002/weights
    API->>SVC: get_snapshot("CUST-002")

    SVC->>DB: Resolve external_id → customer UUID
    SVC->>DB: Query active CustomerWeightProfile

    alt Profile exists
        SVC->>SVC: For each indicator: effective = baseline × multiplier
        SVC->>SVC: Compute diff, assign status (stable / limited / baseline)
        SVC->>SVC: Sort by absolute difference descending
        SVC-->>UI: Snapshot: indicator table + blend comparison + status
    else No profile
        SVC-->>UI: Snapshot: all baseline weights, status = "baseline fallback"
    end
```

---

## Reset Flow

```mermaid
sequenceDiagram
    participant UI as ScoringFactorsDrawer
    participant API as /api/customers/:id/weights/reset
    participant SVC as CustomerWeightExplainService
    participant DB as PostgreSQL

    UI->>API: POST /api/customers/CUST-002/weights/reset
    API->>SVC: reset_to_baseline("CUST-002")

    SVC->>DB: Deactivate current profile (is_active = false)
    Note over DB: Profile preserved for audit, not deleted

    SVC-->>UI: Reset confirmed — baseline restored
    Note over UI: Next investigation uses default weights
```

---

## Key Files

| File | Purpose |
|------|---------|
| `app/api/routes/customer_weights.py` | 3 endpoints: snapshot, history, reset |
| `app/api/schemas/customer_weights.py` | `WeightSnapshotResponse`, `WeightHistoryResponse`, `WeightResetRequest` |
| `app/services/control/customer_weight_explain_service.py` | `get_snapshot()`, `get_history()`, `reset_to_baseline()` |
| `app/core/weight_context.py` | `build_weight_context()` — profile → prompt string |
| `app/core/calibration.py` | `recalculate_profile()`, `calculate_blend_weights()`, `apply_decay()` |
| `app/services/feedback/feedback_loop_service.py` | `process_decision()` — triggers calibration |
| `app/data/db/models/customer_weight_profile.py` | `CustomerWeightProfile` ORM model |

## See Also

- Detailed design: `design_module.md`
- Benchmark outputs: `outputs/blend_feedback_benchmark/sweep_20260211_101330/`
