# Nexa Backend — Architecture Overview

Nexa is a fraud detection platform for financial withdrawals. It combines **rule-based scoring**, **LLM-powered investigators**, and **autonomous background auditing** to produce approve / escalate / block decisions on withdrawal requests.

---

## System Architecture

```mermaid
graph TD
    subgraph Clients
        UI[Admin UI]
        EXT[External Systems\nwithdrawal events]
    end

    subgraph API Layer
        direction LR
        FRAUD[/withdrawals/investigate]
        AUDIT[/background-audits]
        PREFRAUD[/prefraud]
        ANALYTICS[/analytics/query]
        CONTROL[/admins /alerts\n/customer-weights]
    end

    subgraph Services Layer
        IS[InvestigatorService]
        BAF[BackgroundAuditFacade]
        DET[DetectionService]
        POST[PostureService]
        FLS[FeedbackLoopService]
        SS[StreamingService]
    end

    subgraph Agentic System
        BA[BaseAgent\nGemini LLM]
        INV[Investigators\nfinancial · identity · cross_account]
        AUDIT_AG[BackgroundAuditAgent]
        DRIFT_AG[WeightDriftAgent]
    end

    subgraph Core Layer
        SC[Scoring Engine]
        CAL[Calibration]
        WD[Weight Drift]
        PF[Pattern Fingerprint]
    end

    subgraph Data Layer
        PG[(PostgreSQL\n20+ tables)]
        CHROMA[(ChromaDB\nvector store)]
        EMB[Gemini Embeddings]
    end

    UI --> API Layer
    EXT --> FRAUD

    FRAUD --> IS
    AUDIT --> BAF
    PREFRAUD --> DET
    PREFRAUD --> POST
    ANALYTICS --> SS
    CONTROL --> FLS

    IS --> SC
    IS --> CAL
    IS -->|runs| INV
    INV --> BA
    BAF -->|runs| AUDIT_AG
    BAF -->|runs| DRIFT_AG
    AUDIT_AG --> BA
    DRIFT_AG --> BA

    IS --> PG
    BAF --> PG
    BAF --> CHROMA
    EMB --> CHROMA
    FLS --> CAL
    FLS --> PG
    DET --> PG
    POST --> PG
```

---

## Module Docs

| Module | README |
|--------|--------|
| Agentic System | [docs/agentic_system/README.md](agentic_system/README.md) |
| API Layer | [docs/api/README.md](api/README.md) |
| Core Layer | [docs/core/README.md](core/README.md) |
| Data Layer | [docs/data/README.md](data/README.md) |
| Services Layer | [docs/services/README.md](services/README.md) |

---

## Key Flows

### 1. Withdrawal Investigation

```
POST /withdrawals/investigate
  -> InvestigatorService.investigate()
    -> run_all_indicators()          # 8 rule-based scores (parallel DB queries)
    -> calculate_risk_score()        # weighted composite + overrides
    -> [if not auto-approved]
      -> 3 LLM investigators         # financial, identity, cross_account (parallel)
      -> triage verdict LLM          # final synthesized decision
    -> apply_verdict()               # rule + triage + posture uplift
    -> persist to DB
    -> create alert if blocked/escalated
  <- InvestigatorResponse
```

### 2. Background Audit Run

```
POST /background-audits/trigger
  -> BackgroundAuditFacade.trigger_run()
    -> extract_cohort()              # DB: fetch recent flagged evaluations
    -> embed_and_cluster()           # Gemini embeddings -> HDBSCAN clusters
    -> [parallel]
      -> generate_candidates()       # per cluster: BackgroundAuditAgent synthesis
      -> run_weight_drift_analysis() # WeightDriftAgent on fleet profiles
    -> store AuditCandidates in DB
  <- run_id (SSE stream at /runs/{id}/stream)
```

### 3. Officer Decision -> Weight Recalibration

```
POST /admins/decision {withdrawal_id, action: "blocked"|"approved"}
  -> FeedbackLoopService
    -> load decision window (last 20 decisions)
    -> recalculate_profile()         # Bayesian precision per indicator
    -> calculate_blend_weights()     # rule_engine vs investigator ratio
    -> update CustomerWeightProfile in DB
```

---

## Layering Rules

```
API -> Service -> Core / Data
```

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| API | Services, API Schemas | DB Models, Core directly |
| Services | Core, Data, Agentic System | API Schemas |
| Core | nothing (pure functions) | Services, Data, Agentic System |
| Data | DB Models, SQLAlchemy | Core, Services, API |
| Agentic System | Data (vector store) | Services, Core |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web framework | FastAPI (async) |
| LLM | Google Gemini (via LangChain 1.0) |
| Database | PostgreSQL (async via asyncpg/SQLAlchemy) |
| Vector store | ChromaDB (HNSW cosine) |
| Embeddings | Google Gemini `embedding-001` (768-dim) |
| Clustering | HDBSCAN (density-based, noise-tolerant) |
| Agent framework | LangChain `create_agent` |
| Web search | Tavily (optional, fraud typology research) |
| Progress streaming | Server-Sent Events (SSE) |
