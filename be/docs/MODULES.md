# Backend Module Documentation

Quick reference to all backend module READMEs.

## Module READMEs

### 1. Agentic System (`be/app/agentic_system/`)
**File**: `be/docs/agentic_system/README.md`

AI-powered fraud investigation using LangChain agents with Google Gemini LLM.

**Key Components**:
- `BaseAgent` — LangChain wrapper supporting streaming, structured output, tool-calling
- `BackgroundAuditAgent` — Autonomous fraud pattern investigator
- `WeightDriftAgent` — Autonomous weight drift investigator
- SQL toolkit with read-only middleware for safety
- KMeans clustering tool on ChromaDB embeddings
- Chart rendering + web search tools

**Design**: Composition over inheritance. Agents own a BaseAgent, never subclass. ReadOnlySQLMiddleware auto-injected. Schema injected at construction time.

---

### 2. API Layer (`be/app/api/`)
**File**: `be/docs/api/README.md`

FastAPI routers organized by domain. Zero business logic — all work delegated to services.

**Route Groups**:
- `fraud/` — `/withdrawals/investigate`, `/payout`, `/submit`
- `prefraud/` — `/posture`, `/signals`, `/background-audits`
- `analytics/` — `/dashboard`, `/query` (streaming), `/transactions`
- `control/` — `/alerts`, `/admins`, `/customer-weights`

**Design**: Services injected via `app.state`. SSE for background audit progress. Schemas separate from DB models.

---

### 3. Core Layer (`be/app/core/`)
**File**: `be/docs/core/README.md`

Pure business logic — no DB access, no HTTP calls. Deterministic, testable, side-effect-free.

**Modules**:
- `scoring.py` — Risk score engine with thresholds (APPROVE=0.30, BLOCK=0.70, etc.)
- `calibration.py` — Per-customer weight adjustment using Bayesian smoothing
- `weight_drift.py` — Drift analytics (IQR-based outlier detection)
- `pattern_fingerprint.py` — Extract fraud pattern signatures
- `indicators/` — 8 indicators (query + scorer pattern enforces purity)

**Design**: Splitting query/scorer enforces DB-only in queries, pure functions in scorers.

---

### 4. Data Layer (`be/app/data/`)
**File**: `be/docs/data/README.md`

Async SQLAlchemy ORM with PostgreSQL. Models, repositories, vector store.

**Core Models**:
- `Customer`, `Withdrawal`, `Evaluation`, `IndicatorResult`
- `CustomerWeightProfile`, `CustomerRiskPosture` (JSONB flex fields)
- `WithdrawalDecision`, `Alert`

**Repositories**: `BaseRepository<T>` pattern. Encapsulates all DB logic.

**Vector Store**: ChromaDB with Gemini embeddings for background audit clustering.

**Design**: Async-only, no lazy loading. Expunge objects before leaving session. JSONB for flex fields avoids schema migrations.

---

### 5. Services Layer (`be/app/services/`)
**File**: `be/docs/services/README.md`

Orchestrates business workflows using Core logic and Data repositories. Only layer touching both.

**Service Groups**:
- `fraud/` — `InvestigatorService` (full pipeline: indicators → score → LLM investigators → triage → verdict)
- `background_audit/` — `BackgroundAuditFacade` (extract → embed/cluster → patterns + drift analysis)
- `prefraud/` — `DetectionService` + `PostureService` (5 pattern detectors, 7 risk signals)
- `control/` — `FeedbackLoopService`, `AlertService`, `DecisionService`, etc.
- `chat/` — `StreamingService` (analyst chat with SSE + conversation history)

**Design**: Facade pattern for complex pipelines. Parallel asyncio.gather where possible. Fire-and-forget feedback loops.

---

## Layering Rules

```
API → Service → Core / Data
```

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| API | Services, Schemas | DB Models, Core directly |
| Services | Core, Data, Agentic System | API Schemas |
| Core | nothing (pure functions) | Services, Data, Agentic System |
| Data | DB Models, SQLAlchemy | Core, Services, API |
| Agentic System | Data (vector store) | Services, Core |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Web framework | FastAPI (async) |
| LLM | Google Gemini 3-flash-preview (via LangChain 1.0) |
| Database | PostgreSQL (async via asyncpg + SQLAlchemy) |
| Vector store | ChromaDB (HNSW cosine) |
| Embeddings | Google Gemini `embedding-001` (768-dim) |
| Clustering | HDBSCAN (density-based) |
| Agent framework | LangChain `create_agent` |
| Streaming | Server-Sent Events (SSE) |

---

## Key Flows

### Withdrawal Investigation

```
POST /withdrawals/investigate
  → InvestigatorService.investigate()
    → run_all_indicators()              # 8 rule-based scores (parallel)
    → calculate_risk_score()            # weighted composite
    → [if not auto-approved]
      → 3 LLM investigators (parallel)  # financial, identity, cross_account
      → triage verdict LLM              # final synthesis
    → apply_verdict()                   # rule + triage + posture
    → persist to DB + create alert
```

### Background Audit Run

```
POST /background-audits/trigger
  → BackgroundAuditFacade.trigger_run()
    → extract_cohort()                  # DB: flagged evaluations
    → embed_and_cluster()               # Gemini embeddings + HDBSCAN
    → [parallel]
      → generate_candidates()           # BackgroundAuditAgent per cluster
      → run_weight_drift_analysis()     # WeightDriftAgent
    → store AuditCandidate rows
```

### Officer Decision → Weight Recalibration

```
POST /admins/decision {withdrawal_id, action: "blocked"|"approved"}
  → FeedbackLoopService
    → load decision window (last 20)
    → recalculate_profile()             # Bayesian precision per indicator
    → calculate_blend_weights()         # rule vs investigator ratio
    → update CustomerWeightProfile in DB
```
