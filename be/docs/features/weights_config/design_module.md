# Design Module — Weighting System

How customer-specific weights affect scoring, LLM prompts, and blend ratios across one full calibration cycle.

---

## What Gets Adapted (3 Things)

```mermaid
flowchart LR
    PROFILE[CustomerWeightProfile] --> IW[Indicator Multipliers<br/>e.g. velocity 1.9x]
    PROFILE --> BW[Blend Weights<br/>e.g. 55% rule / 45% investigator]
    PROFILE --> PC[Prompt Context<br/>injected into triage + investigators]

    IW --> SCORING[Rule Engine Scoring]
    BW --> BLEND[Final Decision Fusion]
    PC --> LLM[LLM Agent Prompts]
```

---

## Full Calibration Cycle

```mermaid
sequenceDiagram
    participant UI as Officer UI
    participant INV as InvestigatorService
    participant DB as PostgreSQL
    participant LLM as Triage / Investigators
    participant FB as FeedbackLoopService
    participant CAL as Calibration Engine

    Note over UI,CAL: PHASE 1 — Investigation (uses current profile)

    UI->>INV: POST /investigate
    INV->>DB: Load active CustomerWeightProfile
    INV->>INV: effective_weight = baseline × multiplier
    INV->>INV: build_weight_context(profile)
    INV->>LLM: Triage prompt + weight context
    LLM-->>INV: Investigator assignments
    INV->>LLM: Investigator prompts + weight context
    LLM-->>INV: Findings
    INV->>INV: Blend scores (per-customer blend weights)
    INV->>DB: Save Evaluation
    INV-->>UI: Decision + risk_score

    Note over UI,CAL: PHASE 2 — Officer Decision (triggers recalibration)

    UI->>FB: POST /payout/decision (approve/block)
    FB->>DB: Fetch decision window + indicators
    FB->>CAL: recalculate_profile(decisions)
    CAL->>CAL: calculate_indicator_multiplier per indicator
    CAL->>CAL: calculate_blend_weights
    CAL->>CAL: apply_decay (if inactive > 90 days)
    CAL->>DB: Save new active CustomerWeightProfile

    Note over UI,INV: PHASE 3 — Next investigation uses updated profile
```

---

## How Effective Weights Are Built

```mermaid
flowchart TD
    REQ[Investigation Request] --> LOAD{Active profile exists?}

    LOAD -->|No| BASELINE[Use baseline INDICATOR_WEIGHTS<br/>from scoring.py]
    LOAD -->|Yes| MULTIPLY[For each indicator:<br/>effective = baseline × multiplier]

    BASELINE --> RUN[Run 8 Indicators]
    MULTIPLY --> RUN

    RUN --> COMPOSITE["composite = Σ(score × effective_weight) / Σ(effective_weight)"]
    COMPOSITE --> DECISION{composite value?}

    DECISION -->|"< 0.30"| APPROVE[approved — fast path, 0 LLM calls]
    DECISION -->|"0.30 – 0.70"| ESCALATE[escalated — run triage + investigators]
    DECISION -->|">= 0.70"| BLOCK[blocked — fast path, 0 LLM calls]

    classDef fast fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef slow fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    class APPROVE,BLOCK fast
    class ESCALATE slow
```

---

## How Weight Context Reaches LLM Prompts

```mermaid
flowchart TD
    PROFILE[CustomerWeightProfile] --> BUILD["build_weight_context(indicator_weights, blend_weights)"]

    BUILD --> GATES{Display gates per indicator}

    GATES -->|"multiplier < 0.85"| DAMP["Dampened: historically over-sensitive"]
    GATES -->|"multiplier > 1.15"| BOOST["Boosted: historically significant"]
    GATES -->|"abs(m - 1.0) >= 0.08"| WATCH["Emerging watchlist"]
    GATES -->|"sample_size < 2"| SKIP[Suppressed — not shown]

    DAMP --> CTX[Weight context string]
    BOOST --> CTX
    WATCH --> CTX

    CTX --> TRIAGE["TRIAGE_ROUTER_PROMPT.format(weight_context=...)"]
    CTX --> INV["build_investigator_prompt(..., weight_context=...)"]

    BLEND_LINE["Blend stance line — always shown"] --> CTX

    classDef suppress fill:#ccc,stroke:#333,stroke-width:1px,color:#666
    class SKIP suppress
```

| Gate | Condition | What the LLM sees |
|------|-----------|-------------------|
| Dampened | multiplier < 0.85 | "This indicator is historically over-sensitive for this customer" |
| Boosted | multiplier > 1.15 | "This indicator is historically significant for this customer" |
| Emerging | abs(m - 1.0) >= 0.08 | Flagged, not yet dampened/boosted |
| Blend stance | Always shown | "leans rule-engine", "leans investigator", or "balanced" |
| Suppressed | sample_size < 2 | Not included in context |

---

## How Blend Weights Work in Final Decision

```mermaid
flowchart TD
    RULE_SCORE[Rule Engine Composite Score] --> BLEND
    INV_SCORE[Investigator Weighted Average] --> BLEND

    BLEND["blended = rule_score × rule_w + inv_score × inv_w"]

    PROFILE_BW[Profile blend_weights<br/>e.g. {rule: 0.55, investigator: 0.45}] --> BLEND
    DEFAULT["Default: 0.60 / 0.40<br/>(if no profile)"] -.-> BLEND

    BLEND --> FINAL{blended value?}
    FINAL -->|">= 0.70 OR any investigator >= 0.7"| BLOCKED[blocked]
    FINAL -->|">= 0.30"| ESCALATED[escalated]
    FINAL -->|"< 0.30"| APPROVED[approved]

    GUARD["Safeguard: rule engine escalation<br/>can never be downgraded"] -.-> FINAL
```

---

## How Calibration Recalculates Weights

```mermaid
sequenceDiagram
    participant FB as FeedbackLoopService
    participant DB as PostgreSQL
    participant CAL as Calibration Engine

    FB->>DB: Fetch recent decisions for this customer
    DB-->>FB: Decision window (last N decisions)

    FB->>DB: Fetch indicator scores from evaluations
    DB-->>FB: Per-indicator scores + officer actions

    FB->>CAL: recalculate_profile(decisions, current_profile)

    loop For each indicator
        CAL->>CAL: Compare rule signal vs officer action
        Note over CAL: Officer overruled rule? → adjust multiplier
        Note over CAL: Officer agreed? → reinforce multiplier
        CAL->>CAL: calculate_indicator_multiplier(history)
    end

    CAL->>CAL: calculate_blend_weights(decisions)
    Note over CAL: Rule engine accurate? → increase rule weight
    Note over CAL: Investigators accurate? → increase inv weight

    CAL->>CAL: apply_decay (if last decision > 90 days ago)

    CAL->>DB: Deactivate old profile
    CAL->>DB: Save new active CustomerWeightProfile
```

---

## Profile Lifecycle

```mermaid
stateDiagram-v2
    [*] --> BaselineFallback: No profile exists

    BaselineFallback --> LimitedData: First decisions collected

    LimitedData --> Stable: sample_count >= 5
    Stable --> Stable: New decisions recalibrate

    Stable --> Damped: Inactivity > 90 days
    Damped --> Stable: Fresh decisions arrive

    LimitedData --> BaselineFallback: Officer resets
    Stable --> BaselineFallback: Officer resets
    Damped --> BaselineFallback: Officer resets
```

| State | Scoring | Prompt context | Blend |
|-------|---------|---------------|-------|
| BaselineFallback | Default weights | None injected | 60/40 default |
| LimitedData | Multipliers applied (cautious) | Shown with "limited data" caveat | Slightly adapted |
| Stable | Multipliers fully applied | Full context (dampened/boosted tags) | Fully adapted |
| Damped | Multipliers decayed toward 1.0 | Reduced confidence context | Decayed toward default |

---

## Class Diagram

```mermaid
classDiagram
    class InvestigatorService {
        +investigate(request)
        -_run_triage(context, weight_context)
        -_run_investigators(...)
        -_compute_decision(...)
    }

    class FeedbackLoopService {
        +process_decision(withdrawal_id, evaluation_id, action)
        -_recalibrate_weights(customer_id)
    }

    class Calibration {
        +recalculate_profile(decisions, profile)
        +calculate_blend_weights(decisions)
        +calculate_indicator_multiplier(history)
        +apply_decay(profile)
    }

    class WeightContext {
        +build_weight_context(indicator_weights, blend_weights)
    }

    class CustomerWeightProfile {
        indicator_weights: JSONB
        blend_weights: JSONB
        decision_window: JSONB
        is_active: bool
        recalculated_at: datetime
    }

    InvestigatorService --> WeightContext : builds prompt context
    FeedbackLoopService --> Calibration : triggers recalibration
    Calibration --> CustomerWeightProfile : writes new profile
    FeedbackLoopService ..> CustomerWeightProfile : reads current
```

---

## Key Files

| File | Purpose |
|------|---------|
| `app/core/scoring.py` | `INDICATOR_WEIGHTS` baseline + `calculate_risk_score()` |
| `app/core/weight_context.py` | `build_weight_context()` — profile → prompt string |
| `app/core/calibration.py` | `recalculate_profile()`, `calculate_blend_weights()`, `apply_decay()` |
| `app/services/fraud/investigator_service.py` | Loads profile, applies effective weights, injects context |
| `app/services/feedback/feedback_loop_service.py` | `process_decision()` → triggers calibration |
| `app/data/db/models/customer_weight_profile.py` | `CustomerWeightProfile` ORM model |

## Benchmark Artifacts

Live sweep outputs with per-step prompt snapshots:
- `outputs/blend_feedback_benchmark/sweep_20260211_101330/blend_feedback_sweep_summary.json`
- `outputs/blend_feedback_benchmark/sweep_20260211_101330/prompt_context_evolution_sweep.csv`
