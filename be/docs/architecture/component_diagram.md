# Component Diagram

High-level system architecture focusing on API routes and their primary functions.

---

## System Overview

```mermaid
graph TB
    FE[Frontend — nexa-fe] --> API[API Layer]

    subgraph API["API Routes — app/api/routes/"]
        direction TB

        subgraph FRAUD["Fraud Detection"]
            INV[POST /withdrawals/investigate<br/>Run NEW pipeline]
            SUB[POST /withdrawal/submit<br/>Submit withdrawal + evaluate]
            EVAL[GET /payout/evaluate/:id<br/>Get stored results]
            QUEUE[GET /payout/queue<br/>Review queue]
            DEC[POST /payout/decision<br/>Officer approve/block]
            EVID[GET /payout/investigate/:id<br/>Get evidence]
        end

        subgraph PREFRAUD["Pre-Fraud Detection"]
            POST[GET /customers/:id/risk-posture<br/>Current posture]
            RCOMP[POST /customers/:id/risk-posture/recompute<br/>Manual recompute]
            RHIST[GET /customers/:id/risk-posture/history<br/>Posture history]
            PLIST[GET /patterns<br/>List patterns]
            PDET[GET /patterns/:id<br/>Pattern detail]
            PACT[POST /patterns/:id/activate<br/>Activate pattern]
            AUDIT[POST /background-audits/trigger<br/>Trigger audit run]
        end

        subgraph CONTROL["Control & Alerts"]
            ALERT[GET /alerts<br/>List fraud alerts]
            BULK[POST /alerts/bulk-action<br/>Bulk actions]
            CARD[POST /alerts/card-lockdown<br/>Lock shared cards]
            WT[GET /customers/:id/weights<br/>Weight snapshot]
            WHI[GET /customers/:id/weights/history<br/>Weight history]
            WRES[POST /customers/:id/weights/reset<br/>Reset weights]
        end

        subgraph ANALYTICS["Analytics & Query"]
            DASH[GET /dashboard/stats<br/>Dashboard stats]
            QRY[POST /query<br/>Keyword search]
            CHAT[POST /query/chat<br/>LLM chat SSE]
            TXN[GET /transactions<br/>Transaction list]
            EXP[GET /transactions/export<br/>CSV export]
        end

        subgraph OTHER["Other"]
            CUST[GET /customers<br/>List customers]
            SET[GET/POST /settings<br/>Thresholds config]
            HEALTH[GET /health<br/>Health check]
        end
    end

    API --> SERVICES[Service Layer]
    SERVICES --> DB[(PostgreSQL)]
    SERVICES --> LLM[Gemini API]

    classDef fraud fill:#E74C3C,stroke:#333,stroke-width:2px,color:#fff
    classDef prefraud fill:#9B59B6,stroke:#333,stroke-width:2px,color:#fff
    classDef control fill:#F39C12,stroke:#333,stroke-width:2px,color:#fff
    classDef analytics fill:#3498DB,stroke:#333,stroke-width:2px,color:#fff
    classDef other fill:#95A5A6,stroke:#333,stroke-width:2px,color:#fff
    classDef ext fill:#27AE60,stroke:#333,stroke-width:2px,color:#fff

    class INV,SUB,EVAL,QUEUE,DEC,EVID fraud
    class POST,RCOMP,RHIST,PLIST,PDET,PACT,AUDIT prefraud
    class ALERT,BULK,CARD,WT,WHI,WRES control
    class DASH,QRY,CHAT,TXN,EXP analytics
    class CUST,SET,HEALTH other
    class SERVICES,DB,LLM ext
```

---

## API Route Summary

### Fraud Detection (6 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/withdrawals/investigate` | Run NEW fraud pipeline (rule engine → triage → investigators) |
| POST | `/withdrawal/submit` | Submit withdrawal + run fraud check |
| GET | `/payout/evaluate/{id}` | Get stored indicator results for a withdrawal |
| GET | `/payout/queue` | Get pending escalated withdrawals for officer review |
| POST | `/payout/decision` | Officer approves or blocks a flagged withdrawal |
| GET | `/payout/investigate/{id}` | Get investigation evidence for a withdrawal |

**Files:**
- `app/api/routes/fraud/investigate.py` — NEW pipeline endpoint
- `app/api/routes/fraud/withdrawal_submit.py` — Withdrawal submission
- `app/api/routes/fraud/payout.py` — Queue, decisions, evidence

---

### Pre-Fraud Detection (7 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/customers/{id}/risk-posture` | Get current risk posture for a customer |
| POST | `/customers/{id}/risk-posture/recompute` | Trigger manual posture recompute |
| GET | `/customers/{id}/risk-posture/history` | Get posture snapshot history |
| GET | `/patterns` | List fraud patterns (with filters) |
| GET | `/patterns/{id}` | Get pattern detail with matched customers |
| POST | `/patterns/{id}/activate` | Activate a pattern (candidate → active) |
| POST | `/background-audits/trigger` | Trigger background audit run |

**Files:**
- `app/api/routes/prefraud/prefraud.py` — Risk posture endpoints
- `app/api/routes/prefraud/patterns.py` — Pattern lifecycle
- `app/api/routes/prefraud/background_audits.py` — Background audits

---

### Control & Alerts (6 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/alerts` | Get fraud alerts with computed patterns |
| POST | `/alerts/bulk-action` | Process bulk actions on alerts |
| POST | `/alerts/card-lockdown` | Lock all accounts sharing a blocked card |
| GET | `/customers/{id}/weights` | Get baseline vs customer weight comparison |
| GET | `/customers/{id}/weights/history` | Get weight profile change audit trail |
| POST | `/customers/{id}/weights/reset` | Reset customer to baseline weights |

**Files:**
- `app/api/routes/control/alerts.py` — Alert management
- `app/api/routes/control/customer_weights.py` — Adaptive weight system

---

### Analytics & Query (5 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/dashboard/stats` | Dashboard overview with aggregated stats |
| POST | `/query` | Keyword-based fraud search (JSON response) |
| POST | `/query/chat` | LLM-powered analyst chat (SSE streaming) |
| GET | `/transactions` | Paginated withdrawal history with evaluations |
| GET | `/transactions/export` | Download transaction history as CSV |

**Files:**
- `app/api/routes/analytics/dashboard.py` — Dashboard stats
- `app/api/routes/analytics/query.py` — Search & chat
- `app/api/routes/analytics/transactions.py` — Transaction history

---

### Other (3 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/customers` | List all customers with external_id, name, country |
| GET | `/settings` | Get active threshold config |
| POST | `/settings` | Save new threshold configuration |
| GET | `/health` | Service health status |

**Files:**
- `app/api/routes/customer/customers.py` — Customer list
- `app/api/routes/settings/settings.py` — Config management
- `app/api/routes/system/health.py` — Health check

---

## Endpoint Count by Category

| Category | Endpoints | Router Files |
|----------|-----------|--------------|
| **Fraud Detection** | 6 | 3 (investigate, withdrawal_submit, payout) |
| **Pre-Fraud Detection** | 7 | 3 (prefraud, patterns, background_audits) |
| **Control & Alerts** | 6 | 2 (alerts, customer_weights) |
| **Analytics & Query** | 5 | 3 (dashboard, query, transactions) |
| **Other** | 3 | 3 (customers, settings, health) |
| **Total** | **27** | **14 router files** |

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│  API Routes (27 endpoints)                          │
│  - Validation                                       │
│  - Routing                                          │
│  - Response formatting                              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Service Layer                                      │
│  - Business logic orchestration                     │
│  - Cross-cutting concerns                           │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐  ┌─────────┐  ┌─────────┐
   │   Core   │  │ Agentic │  │  Data   │
   │  Logic   │  │ System  │  │  Layer  │
   └────┬─────┘  └────┬────┘  └────┬────┘
        │             │            │
        │             ▼            ▼
        │        ┌─────────┐  ┌──────────┐
        │        │ Gemini  │  │   PostgreSQL  │
        │        │   API   │  │              │
        └────────┴─────────┴──┴──────────────┘
```

---

## Two Fraud Pipelines

### OLD Pipeline: `/payout/evaluate` (deprecated)
- Rule Engine → Gray Zone LLM → Optional 5-LLM comparison
- Avg latency: ~21s with LLM, ~0.3s rule-only
- **See:** `app/services/fraud/check_service.py`

### NEW Pipeline: `/withdrawals/investigate`
- Rule Engine → Skip Triage Gate → Triage Router → 0-3 Investigators → Blended Scoring
- Clean cases (56%): **0.14s** (0 LLM calls)
- Suspicious cases (44%): **12.1s** (2-3 LLM calls)
- Blended (80/20): **~2.8s**
- **See:** `app/services/fraud/investigator_service.py`

---

## External Dependencies

| Dependency | Purpose | Used By |
|------------|---------|---------|
| **PostgreSQL 16** | Primary data store | All services via repositories |
| **Gemini 3-Flash** | Fraud investigation LLM | investigator_service, check_service |
| **Gemini 2.5-Flash** | Analyst chat LLM | streaming_service |

---

## Configuration

Environment variables in `.env`:
- `GOOGLE_API_KEY` — Required for LLM calls
- `POSTGRES_URL` — `postgresql+asyncpg://user:changeme@localhost:15432/fraud_detection`
- Ports: API=18080 (docker) / 8080 (local), DB=15432, ChromaDB=18000

---

---

# Service Layer Architecture

Business logic services — orchestrators between API routes and data layer.

---

## Core Services (Actually Used)

```mermaid
graph TB
    API[API Routes] --> CORE[Core Services]

    subgraph CORE["Active Services — app/services/"]
        direction TB

        subgraph FRAUD["Fraud Pipeline"]
            INV[InvestigatorService<br/>Main fraud detection]
        end

        subgraph PREFRAUD["Pre-Fraud (Background)"]
            POST[PostureService<br/>Risk posture]
            DET[DetectionService<br/>Pattern detection]
            SCH1[posture_scheduler<br/>Auto-recompute every 6h]
            SCH2[detection_scheduler<br/>Auto-detect every 12h]
        end

        subgraph CONTROL["Control & Helpers"]
            FB[FeedbackLoopService<br/>Learn from decisions]
            ALT[alert_service<br/>Alert CRUD]
            DEC[decision_service<br/>Officer decisions]
            EVID[evidence_service<br/>Investigation data]
            WD[withdrawal_service<br/>Withdrawal lifecycle]
            WT[customer_weight_explain<br/>Adaptive weights UI]
            CARD[card_lockdown<br/>Shared card blocking]
            THR[threshold_service<br/>Config CRUD]
        end

        subgraph ANALYTICS["Analytics"]
            CHAT[StreamingService<br/>LLM chat SSE]
            QRY[query_service<br/>Keyword search]
        end

        subgraph BGAUDIT["Background Audit (Optional)"]
            AUD[BackgroundAuditFacade<br/>LLM-based pattern mining]
        end
    end

    API --> INV
    API --> POST
    API --> DET
    API --> FB
    API --> ALT
    API --> DEC
    API --> EVID
    API --> WD
    API --> WT
    API --> CARD
    API --> THR
    API --> CHAT
    API --> QRY
    API --> AUD

    INV --> DB[(PostgreSQL)]
    POST --> DB
    DET --> DB
    FB --> DB
    ALT --> DB
    DEC --> DB
    EVID --> DB
    WD --> DB
    WT --> DB
    CARD --> DB
    THR --> DB
    CHAT --> DB
    QRY --> DB
    AUD --> DB

    INV --> LLM[Gemini 3-Flash]
    CHAT --> LLM2[Gemini 2.5-Flash]
    AUD --> LLM

    SCH1 --> POST
    SCH2 --> DET

    classDef fraud fill:#E74C3C,stroke:#333,stroke-width:2px,color:#fff
    classDef prefraud fill:#9B59B6,stroke:#333,stroke-width:2px,color:#fff
    classDef control fill:#F39C12,stroke:#333,stroke-width:2px,color:#fff
    classDef analytics fill:#3498DB,stroke:#333,stroke-width:2px,color:#fff
    classDef audit fill:#16A085,stroke:#333,stroke-width:2px,color:#fff
    classDef ext fill:#95A5A6,stroke:#333,stroke-width:2px,color:#000

    class INV fraud
    class POST,DET,SCH1,SCH2 prefraud
    class FB,ALT,DEC,EVID,WD,WT,CARD,THR control
    class CHAT,QRY analytics
    class AUD audit
    class DB,LLM,LLM2 ext
```

---

## Service Summary

### Fraud Pipeline (1 service)

| Service | File | Purpose | Performance |
|---------|------|---------|-------------|
| **InvestigatorService** | `fraud/investigator_service.py` | Rule engine → triage → investigators → blended decision | 0.14s (clean), 12.1s (suspicious) |

**Used by:** `/withdrawals/investigate`, `/withdrawal/submit`

---

### Pre-Fraud (2 services + 2 schedulers)

| Service | File | Purpose | Run Frequency |
|---------|------|---------|---------------|
| **PostureService** | `prefraud/posture_service.py` | Compute customer risk posture from 6 signals | Every 6h (auto) + manual |
| **DetectionService** | `prefraud/detection_service.py` | Run 5 pattern detectors, dedupe with Jaccard | Every 12h (auto) + manual |
| *posture_scheduler* | `prefraud/posture_scheduler.py` | Background task for auto-recompute | Started in `main.py` |
| *detection_scheduler* | `prefraud/detection_scheduler.py` | Background task for auto-detect | Started in `main.py` |

**Used by:** `/customers/{id}/risk-posture`, `/patterns/detect`

**6 Signals (components):** account_maturity, funding_behavior, graph_proximity, infrastructure_stability, payment_risk, velocity_trends

**5 Detectors (components):** card_testing, no_trade_withdrawal, rapid_funding_cycle, shared_device_ring, velocity_burst

---

### Control & Helpers (8 services)

| Service | File | Purpose | Used By |
|---------|------|---------|---------|
| **FeedbackLoopService** | `control/feedback_loop_service.py` | Learn from officer decisions (fire-and-forget) | `/payout/decision` |
| **alert_service** | `control/alert_service.py` | Create/list/bulk-action alerts | `/alerts` |
| **decision_service** | `control/decision_service.py` | Persist officer decisions | `/payout/decision` |
| **evidence_service** | `control/evidence_service.py` | Fetch investigation JSONB | `/payout/investigate/{id}` |
| **withdrawal_service** | `control/withdrawal_service.py` | Withdrawal CRUD helpers | `/withdrawals/investigate`, `/payout/*` |
| **customer_weight_explain** | `control/customer_weight_explain_service.py` | UI for adaptive weights | `/customers/{id}/weights` |
| **card_lockdown** | `control/card_lockdown_service.py` | Lock accounts sharing cards | `/alerts/card-lockdown` |
| **threshold_service** | `control/threshold_service.py` | Config CRUD | `/settings` |

---

### Analytics (2 services)

| Service | File | Purpose | Performance |
|---------|------|---------|-------------|
| **StreamingService** | `chat/streaming_service.py` | LLM chat SSE (Gemini 2.5-Flash) | 2.88s TTFT, 100% accuracy |
| **query_service** | `dashboard/query_service.py` | Keyword-based fraud search | ~0.1s |

**Used by:** `/query/chat` (SSE), `/query` (JSON)

---

### Background Audit (1 facade, optional)

| Service | File | Purpose | Enabled |
|---------|------|---------|---------|
| **BackgroundAuditFacade** | `background_audit/facade.py` | LLM-based pattern mining pipeline | Only if `BACKGROUND_AUDIT_ENABLED=true` |

**Pipeline:** Extract cohort → Embed + cluster (K-means) → LLM investigation → Generate candidates

**Used by:** `/background-audits/trigger`

---

## Service Initialization (main.py)

Services are initialized in `lifespan()` and stored in `app.state`:

```python
# Always initialized
app.state.feedback_loop_service = FeedbackLoopService(AsyncSessionLocal)
app.state.posture_service = PostureService(AsyncSessionLocal)
app.state.detection_service = PatternDetectionService(AsyncSessionLocal)
init_analyst_agent()  # Singleton for chat

# Optional
if settings.BACKGROUND_AUDIT_ENABLED:
    app.state.background_audit_facade = BackgroundAuditFacade(AsyncSessionLocal)
```

**Lazy-loaded:** `InvestigatorService` (created on first request via `_get_service()`)

---

## Service Count

| Domain | Services | Total Files |
|--------|----------|-------------|
| **Fraud** | 1 | 1 + 5 internals |
| **Pre-Fraud** | 2 + 2 schedulers | 4 + 6 signals + 5 detectors |
| **Control** | 8 | 8 + 1 helper |
| **Analytics** | 2 | 2 + 1 charting |
| **Background Audit** | 1 | 1 + 8 components |
| **Total** | **14 active** | **~40 files** |

---

## Key Patterns

### Fire-and-Forget (FeedbackLoopService)

```python
# In payout.py route - doesn't block response
asyncio.create_task(
    feedback_service.process_decision(withdrawal_id, evaluation_id, action)
)
```

### Singleton (StreamingService)

```python
# init_analyst_agent() called once in main.py
_agent: BaseAgent | None = None
```

### Dependency Injection (All services)

```python
class Service:
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory
```

---

## Performance Summary

| Service | Latency | LLM Calls |
|---------|---------|-----------|
| **InvestigatorService** (clean) | 0.14s | 0 |
| **InvestigatorService** (suspicious) | 12.1s | 2-3 |
| **PostureService** | 0.3-0.5s | 0 |
| **DetectionService** | 2-5s | 0 |
| **StreamingService** | 2.88s (TTFT) | 1 |
| **BackgroundAuditFacade** | 45-120s | 3-10 |

---

---

# Core Logic Layer

Pure business logic — scoring algorithms, indicators, calibration math. **Zero dependencies** on HTTP, DB sessions, or LLM calls.

---

## Core Modules

```mermaid
graph TB
    SERVICES[Service Layer] --> CORE[Core Logic Layer]

    subgraph CORE["app/core/ — Pure Business Logic"]
        direction TB

        subgraph SCORING["Scoring Engine"]
            SCORE[scoring.py<br/>Weighted aggregation + thresholds]
            CALIB[calibration.py<br/>Per-customer weight math]
            WCTX[weight_context.py<br/>Weight prompt formatting]
            THR[threshold_manager.py<br/>Threshold CRUD placeholder]
        end

        subgraph INDICATORS["Rule Indicators (8)"]
            BASE[base.py<br/>BaseIndicator interface]
            IND1[amount_anomaly<br/>Z-score vs history]
            IND2[velocity<br/>Frequency spikes]
            IND3[geographic<br/>VPN, country mismatch]
            IND4[device_fingerprint<br/>Unknown/shared devices]
            IND5[trading_behavior<br/>W/D ratio]
            IND6[recipient<br/>Name mismatch]
            IND7[payment_method<br/>New/unverified]
            IND8[card_errors<br/>Failed txns]
        end

        subgraph PATTERN["Pattern Extraction"]
            FP[pattern_fingerprint.py<br/>Fingerprint builder]
        end

        subgraph BGAUDIT["Background Audit Logic"]
            PREP[dataset_prep.py<br/>PII masking, cohort builder]
            ANAL[pattern_analysis.py<br/>HDBSCAN clustering, novelty]
        end
    end

    SERVICES --> SCORE
    SERVICES --> CALIB
    SERVICES --> WCTX
    SERVICES --> BASE
    SERVICES --> FP
    SERVICES --> PREP
    SERVICES --> ANAL

    BASE --> IND1
    BASE --> IND2
    BASE --> IND3
    BASE --> IND4
    BASE --> IND5
    BASE --> IND6
    BASE --> IND7
    BASE --> IND8

    classDef scoring fill:#E67E22,stroke:#333,stroke-width:2px,color:#fff
    classDef indicators fill:#8E44AD,stroke:#333,stroke-width:2px,color:#fff
    classDef pattern fill:#16A085,stroke:#333,stroke-width:2px,color:#fff
    classDef audit fill:#2980B9,stroke:#333,stroke-width:2px,color:#fff
    classDef ext fill:#95A5A6,stroke:#333,stroke-width:2px,color:#000

    class SCORE,CALIB,WCTX,THR scoring
    class BASE,IND1,IND2,IND3,IND4,IND5,IND6,IND7,IND8 indicators
    class FP pattern
    class PREP,ANAL audit
    class SERVICES ext
```

---

## Module Summary

### Scoring Engine (4 files)

| File | Purpose | Key Functions | Used By |
|------|---------|---------------|---------|
| **scoring.py** | Weighted aggregation + decision thresholds | `calculate_risk_score()` → `ScoringResult` | `investigator_service.py` |
| **calibration.py** | Per-customer weight calibration math | `recalculate_profile()`, `calculate_blend_weights()` | `feedback_loop_service.py` |
| **weight_context.py** | Build prompt sections for adaptive weights | `build_weight_context()` → markdown text | `investigator_service.py` (triage prompt) |
| **threshold_manager.py** | Threshold CRUD placeholder (stub) | `get_current_thresholds()`, `update_thresholds()` | Not actively used (future) |

---

### Rule Indicators (9 files: 1 base + 8 implementations)

All indicators implement `BaseIndicator` and return `IndicatorResult(score, confidence, reasoning, evidence)`.

| Indicator | File | Detects | Key Evidence | Typical Score Range |
|-----------|------|---------|--------------|---------------------|
| **base** | `base.py` | N/A (abstract interface) | N/A | N/A |
| **amount_anomaly** | `amount_anomaly.py` | Z-score > 2.5 vs customer avg | avg, std, z_score | 0.0-0.75 |
| **velocity** | `velocity.py` | Frequency spikes (1h/24h/7d windows) | count_1h, count_24h, spike_ratios | 0.0-0.65 |
| **geographic** | `geographic.py` | VPN, country mismatch, multi-country | vpn_flag, country_code, locations | 0.0-1.0 |
| **device_fingerprint** | `device_fingerprint.py` | Unknown device, shared accounts | device_id, device_age, shared_accounts | 0.0-1.0 |
| **trading_behavior** | `trading_behavior.py` | Withdraw/deposit ratio > 1.5 | trade_count, pnl, w_d_ratio | 0.0-1.0 |
| **recipient** | `recipient.py` | Name mismatch, cross-account reuse | recipient_name, account_count | 0.0-1.0 |
| **payment_method** | `payment_method.py` | New method, unverified | method_age_days, verified_flag | 0.0-1.0 |
| **card_errors** | `card_errors.py` | Failed transactions, method churn | failed_txn_count, methods_changed_30d | 0.0-1.0 |

**Run all in parallel:** `run_all_indicators(ctx, session_factory)` in `indicators/__init__.py` (~50ms)

---

### Pattern Extraction (1 file)

| File | Purpose | Key Functions |
|------|---------|---------------|
| **pattern_fingerprint.py** | Extract canonical fingerprint from indicator results + officer action | `extract_fingerprint()` → `{indicator_combination, signal_type, score_band}` |

**Used by:** `feedback_loop_service.py` to persist confirmed fraud/false positive patterns.

---

### Background Audit Logic (2 files)

| File | Purpose | Key Functions |
|------|---------|---------------|
| **dataset_prep.py** | PII masking, cohort query builder, text quality validation | `mask_pii()`, `build_cohort_query()`, `extract_reasoning_units()` |
| **pattern_analysis.py** | HDBSCAN clustering, novelty detection, candidate quality scoring | `assign_clusters()`, `detect_novelty()`, `calculate_candidate_quality()` |

**Used by:** `background_audit/facade.py` service.

---

## Scoring Algorithm

### Decision Thresholds (scoring.py)

| Constant | Value | Effect |
|----------|-------|--------|
| `APPROVE_THRESHOLD` | 0.30 | Score < 0.30 → auto-approve |
| `BLOCK_THRESHOLD` | 0.70 | Score ≥ 0.70 → auto-block |
| `HARD_ESCALATION_THRESHOLD` | 0.80 | Single indicator ≥ 0.80 → force escalate |
| `MULTI_CRITICAL_THRESHOLD` | 0.60 | 4+ indicators ≥ 0.60 → force block |
| `CONCENTRATED_ESCALATION_THRESHOLD` | 0.90 | Top-3 weighted scores sum ≥ 0.90 → force escalate |

### Indicator Weights (scoring.py)

```python
INDICATOR_WEIGHTS = {
    "trading_behavior": 1.5,      # Highest weight
    "device_fingerprint": 1.3,
    "card_errors": 1.2,
    "geographic": 1.0,
    "amount_anomaly": 1.0,
    "velocity": 1.0,
    "payment_method": 1.0,
    "recipient": 1.0,
}
```

### Override Rules

1. **Hard Escalation:** Any single indicator score ≥ 0.80 with confidence ≥ 0.8 → force `escalated`
2. **Multi-Critical:** 4+ indicators ≥ 0.60 with confidence ≥ 0.8 → force `blocked`
3. **Concentrated Risk:** Top-3 weighted scores sum ≥ 0.90 → force `escalated`
4. **Score Alignment:** Display score bumped to match decision threshold (prevents "33% but blocked" UX)

---

## Calibration System

### Per-Customer Adaptive Weights (calibration.py)

Tracks indicator precision (correct_fires / total_fires) per customer from officer feedback:

```python
# Calculate multiplier from precision (0.2x - 3.0x range)
multiplier = 1.0 + (precision - 0.5) * SENSITIVITY  # SENSITIVITY=1.4

# Apply Bayesian smoothing to prevent volatility
smoothed_precision = (correct + 0.5 * 2.0) / (total + 2.0)
```

**Decay:** Multipliers drift back to 1.0 after 90 days without decisions.

**Blend Weights:** Compute rule_engine vs investigators ratio from historical accuracy:

```python
rule_w = 0.5 + (rule_correct - inv_correct) / total * 0.2
rule_w = clamp(rule_w, 0.4, 0.8)  # Bounded 40-80%
```

---

## Indicator Implementation Pattern

All indicators follow this template:

```python
class ExampleIndicator(BaseIndicator):
    name = "example"
    weight = 1.0

    async def evaluate(self, ctx: dict, session: AsyncSession) -> IndicatorResult:
        # 1. Build SQL query
        stmt = select(...).where(...)
        result = await session.execute(stmt)
        data = result.scalars().all()

        # 2. Compute score (0.0-1.0)
        score = min(metric / threshold, 1.0)

        # 3. Build reasoning
        reasoning = f"Found {len(data)} items..."

        # 4. Package evidence
        evidence = {"metric": metric, "threshold": threshold}

        return IndicatorResult(
            indicator_name=self.name,
            score=score,
            confidence=0.85,  # 0.7-1.0 for SQL-based
            reasoning=reasoning,
            evidence=evidence,
        )
```

**Context keys:**
```python
{
    "customer_id": UUID,
    "withdrawal_id": UUID,
    "amount": float,
    "currency": str,
    "device_id": str | None,
    "ip_address": str | None,
    "withdrawal_method_id": UUID,
}
```

---

## Rules

1. **No side effects** — Pure functions only. No HTTP calls, no LLM invocations.
2. **No DB writes** — Indicators read-only via `AsyncSession`.
3. **No lazy loading** — All SQL queries eager-load required data.
4. **Explicit evidence** — Every `IndicatorResult.evidence` must be a dict with keys matching reasoning.
5. **Score bounds** — All scores clamped to [0.0, 1.0].
6. **Confidence mandatory** — Every indicator must return confidence score (typically 0.7-1.0 for SQL-based).
7. **File length cap** — Max 150 lines per file (split if exceeded).

---

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| **Run all 8 indicators** | ~50ms | Parallel execution via `asyncio.gather()` |
| **Calculate risk score** | ~0.1ms | Pure Python math (no I/O) |
| **Recalculate profile** | ~0.5ms | Pure math (Bayesian smoothing) |
| **Build weight context** | ~0.1ms | String formatting |

---

## Used By

| Core Module | Used By (Services) |
|-------------|-------------------|
| **scoring.py** | `investigator_service.py`, `fraud_check_service.py` |
| **calibration.py** | `feedback_loop_service.py` (weight recalculation) |
| **weight_context.py** | `investigator_service.py` (triage prompt builder) |
| **indicators/** | `investigator_service.py`, `fraud_check_service.py` |
| **pattern_fingerprint.py** | `feedback_loop_service.py` (pattern persistence) |
| **background_audit/** | `background_audit/facade.py` service |

---
