# Nexa - AI-Powered Payments Approval & Fraud Intelligence

Built for the Deriv Hackathon. An intelligent fraud detection system that evaluates every withdrawal through 8 parallel rule indicators, escalating ambiguous cases to LLM-powered investigators for officer review.

## Architecture

```
nexa/
├── fe/          # Nuxt 4 + Tailwind CSS dashboard
└── be/          # FastAPI + LangChain + Gemini backend
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 4, TypeScript, Tailwind CSS |
| Backend | FastAPI, LangChain, Gemini |
| Database | PostgreSQL 16 (asyncpg, SQLAlchemy 2.0) |
| Vector DB | ChromaDB |
| Migrations | Alembic |

## Quick Start

### Backend

```bash
cd be
uv sync                          # Install dependencies
docker compose up -d              # Start PostgreSQL + ChromaDB
python -m scripts.seed_data       # Seed test data
uvicorn app.main:app --reload     # Start API server
```

### Frontend

```bash
cd fe
npm install
npm run dev                       # Start dev server
```

## Fraud Detection Pipeline

### End-to-End Flow

```mermaid
graph TD
    A["POST /api/withdrawals/investigate<br/><i>investigator_service.py:69</i>"] --> B["_load_all — parallel gather<br/><i>investigator_service.py:120-128</i>"]
    B --> B1["run_all_indicators (8 SQL)<br/><i>core/indicators/__init__.py</i>"]
    B --> B2["load_customer_profile"]
    B --> B3["get_active_thresholds"]
    B --> B4["load_posture + patterns"]

    B1 --> C["_score_rules → calculate_risk_score<br/><i>scoring.py:45-86</i>"]
    C --> P["_calculate_posture_uplift<br/><i>investigator_service.py:152-164</i>"]
    P --> R["_resolve_triage<br/><i>investigator_service.py:184-206</i>"]

    R --> D{effective == approved?<br/><i>:194</i>}

    D -->|Yes| E["_build_skip_triage<br/>assignments = empty<br/><i>:208-217</i>"]
    D -->|No: escalated or blocked| F["_run_investigators (all 3 parallel)<br/><i>:289-308</i>"]

    F --> T["_run_triage_verdict<br/>1 LLM call synthesizing rules + findings<br/><i>:245-287</i>"]
    T --> V["apply_verdict<br/><i>verdict.py:7-32</i>"]
    E --> V

    V --> V1{assignments empty?<br/><i>verdict.py:24</i>}
    V1 -->|Yes| V2["Return rule engine decision<br/><i>verdict.py:25</i>"]
    V1 -->|No| V3{confidence < 0.5?<br/><i>verdict.py:28</i>}
    V3 -->|Yes| V4["Fall back to rule engine<br/><i>verdict.py:29</i>"]
    V3 -->|No| V5["Triage verdict authoritative<br/><i>verdict.py:32</i>"]

    V2 --> PERSIST["persist_investigation<br/><i>:104-108</i>"]
    V4 --> PERSIST
    V5 --> PERSIST

    classDef rule fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef llm fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000
    classDef persist fill:#9B59B6,stroke:#333,stroke-width:2px,color:#fff

    class B1,C rule
    class F,T llm
    class D,V1,V3 gate
    class PERSIST persist
```

### Rule Engine State Machine

```mermaid
flowchart TD
    SCORE["composite = Σ(score × weight) / Σ(weight)<br/><i>scoring.py:99-109</i>"] --> MC{4+ indicators >= 0.60<br/>with confidence >= 0.8?<br/><i>scoring.py:120-126</i>}

    MC -->|Yes| BLOCKED["BLOCKED<br/><i>scoring.py:149-150</i>"]

    MC -->|No| BT{composite >= 0.70?<br/><i>scoring.py:149</i>}
    BT -->|Yes| BLOCKED

    BT -->|No| HE{Any single indicator >= 0.80<br/>with confidence >= 0.8?<br/><i>scoring.py:112-117</i>}
    HE -->|Yes| ESCALATED["ESCALATED<br/><i>scoring.py:151-152</i>"]

    HE -->|No| CR{Top-3 weighted scores<br/>sum >= 0.90?<br/><i>scoring.py:129-137</i>}
    CR -->|Yes| ESCALATED

    CR -->|No| AT{composite >= 0.30?<br/><i>scoring.py:151</i>}
    AT -->|Yes| ESCALATED
    AT -->|No| APPROVED["APPROVED<br/><i>scoring.py:153</i>"]

    SCORE2["Display score alignment<br/><i>scoring.py:156-172</i>"]
    BLOCKED --> SCORE2
    ESCALATED --> SCORE2
    APPROVED --> SCORE2

    classDef blocked fill:#E74C3C,stroke:#333,stroke-width:2px,color:#fff
    classDef escalated fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef approved fill:#7ED321,stroke:#333,stroke-width:2px,color:#000
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000

    class BLOCKED blocked
    class ESCALATED escalated
    class APPROVED approved
    class MC,BT,HE,CR,AT gate
```

### Verdict Guardrails (post-investigation)

```mermaid
flowchart TD
    START["apply_verdict(scoring, triage, posture_uplift)<br/><i>verdict.py:7</i>"] --> ADJ["adjusted_rule = composite + posture_uplift<br/><i>verdict.py:21</i>"]
    ADJ --> A1{triage.assignments empty?<br/><i>verdict.py:24</i>}

    A1 -->|Yes: auto-decided| RD["Rule engine decision + adjusted score<br/><i>verdict.py:25</i>"]

    A1 -->|No: investigators ran| A2{triage.confidence < 0.5?<br/><i>verdict.py:28</i>}
    A2 -->|Yes: low confidence| RD2["Fall back to rule engine<br/><i>verdict.py:29</i>"]

    A2 -->|No: confident| AUTH["Triage decision + triage risk_score<br/>(can override rule-engine blocks)<br/><i>verdict.py:32</i>"]

    classDef fallback fill:#F5A623,stroke:#333,stroke-width:2px,color:#000
    classDef auth fill:#16A085,stroke:#333,stroke-width:2px,color:#fff
    classDef gate fill:#4A90E2,stroke:#333,stroke-width:2px,color:#000

    class RD,RD2 fallback
    class AUTH auth
    class A1,A2 gate
```

**Key change**: The old guardrail that prevented triage from overriding rule-engine blocks was removed. Triage agents with SQL evidence can now de-escalate a `blocked` to `approved` if they find no corroborative evidence (confidence >= 0.5).

---

## Background Audit Pipeline

```mermaid
graph LR
    A["Trigger Run"] --> B["Extract<br/>2-5s"]
    B --> C["Embed & Cluster<br/>10-30s"]
    C --> D["Parallel Phase"]

    D --> E["Cluster Investigation<br/>LLM agent per cluster"]
    D --> F["Weight Drift Analysis<br/>IQR + drift agent"]

    E --> G["Merge Candidates"]
    F --> G
    G --> H["Store + SSE Complete"]

    style A fill:#e1f5ff,color:#000
    style B fill:#fff4e1,color:#000
    style C fill:#ffe1f5,color:#000
    style E fill:#f5e1ff,color:#000
    style F fill:#e1ffe1,color:#000
    style H fill:#ddd,color:#000
```

---

## Weight Drift Analysis

```mermaid
sequenceDiagram
    participant Facade
    participant Repo as WeightStatsRepository
    participant Core as weight_drift.py
    participant Agent as WeightDriftAgent
    participant DB

    Facade->>Repo: get_profiles_in_interval()
    Repo-->>Facade: WeightProfile[]

    Facade->>Core: build_drift_summary(profiles)
    Core-->>Facade: DriftSummary (per-indicator stats)

    Facade->>Core: detect_outliers() — IQR method
    Core-->>Facade: OutlierResult[]

    Facade->>Core: suggest_countermeasures()
    Core-->>Facade: [{indicator, issue, severity}]

    Facade->>Agent: analyze(evidence_text)
    Agent->>DB: SQL queries (tool use)
    Agent-->>Facade: synthesis + tool_trace

    Facade->>DB: Save AuditCandidate (drift_data embedded)
```

**Drift math** (`app/core/weight_drift.py`):
- **Outlier detection**: IQR-based (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
- **Trend detection**: Linear slope — rising (>0.05), falling (<-0.05), stable
- **Countermeasures**: Flag multipliers >2.0 (overweight), <0.5 (underweight), std >0.5 (volatile)

---

## Analyst Chat (SSE Streaming)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as POST /api/query/chat
    participant Agent as LangChain Agent
    participant LLM as Gemini 3-Flash
    participant DB as PostgreSQL

    FE->>API: {question, session_id}
    API->>Agent: stream_analyst_answer()
    API-->>FE: SSE status: "Thinking..."

    loop Agent reasoning loop
        Agent->>LLM: question + schema context
        LLM-->>Agent: tool_call(sql_db_query)
        API-->>FE: SSE tool_start (SQL preview)
        Agent->>DB: Read-only SQL query
        DB-->>Agent: result rows
        API-->>FE: SSE tool_end (result)

        opt LLM calls render_chart
            LLM-->>Agent: tool_call(render_chart)
            API-->>FE: SSE chart (title, type, rows)
        end
    end

    LLM-->>Agent: final answer text
    loop Token streaming
        API-->>FE: SSE token (chunk)
    end
    API-->>FE: SSE answer (full text)
    API-->>FE: SSE done (tools_used)
```

**Key details**:
- **Server-side memory**: `InMemorySaver` checkpointer keyed by `session_id` — no history sent from frontend
- **Tools**: `sql_db_query` (read-only via middleware) + `render_chart` (bar/line/pie)
- **SSE events**: `status` → `tool_start/tool_end` → `chart` → `token` → `answer` → `done`
- **Error recovery**: Partial answer emitted before error event; client can display what was collected

---

## Component Overview

```mermaid
graph TB
    FE["Frontend (Nuxt 4)"] --> API["API Layer"]

    subgraph API["Key API Routes"]
        INV["POST /withdrawals/investigate"]
        QUEUE["GET /payout/queue"]
        AUDIT["POST /background-audits/trigger"]
        DRIFT_PDF["GET /runs/:id/drift-pdf"]
        PIN["POST /customers/:id/weights/pin"]
        CHAT["POST /query/chat"]
    end

    subgraph SERVICES["Service Layer"]
        IS["InvestigatorService"]
        BAF["BackgroundAuditFacade"]
        WDA["WeightDriftAnalysis"]
        SS["StreamingService"]
    end

    subgraph CORE["Core Logic (pure math)"]
        SCORE["scoring.py"]
        CALIB["calibration.py"]
        WD["weight_drift.py"]
        IND["8 Indicators"]
    end

    subgraph AGENTS["Agentic System"]
        TRIAGE["Triage Router"]
        INV_AGENTS["3 Investigators"]
        DRIFT_AGENT["WeightDriftAgent"]
        AUDIT_AGENT["BackgroundAuditAgent"]
    end

    INV --> IS
    QUEUE --> IS
    AUDIT --> BAF
    DRIFT_PDF --> BAF
    PIN --> CALIB
    CHAT --> SS

    IS --> SCORE
    IS --> IND
    IS --> TRIAGE
    IS --> INV_AGENTS
    BAF --> WDA
    BAF --> AUDIT_AGENT
    WDA --> WD
    WDA --> DRIFT_AGENT

    SERVICES --> DB[(PostgreSQL)]
    AGENTS --> LLM["Gemini 3-Flash"]

    classDef fraud fill:#E74C3C,stroke:#333,stroke-width:2px,color:#fff
    classDef audit fill:#16A085,stroke:#333,stroke-width:2px,color:#fff
    classDef core fill:#E67E22,stroke:#333,stroke-width:2px,color:#fff
    classDef agent fill:#9B59B6,stroke:#333,stroke-width:2px,color:#fff
    classDef ext fill:#95A5A6,stroke:#333,stroke-width:2px,color:#000

    class IS,INV,QUEUE fraud
    class BAF,WDA,AUDIT,DRIFT_PDF,PIN audit
    class SCORE,CALIB,WD,IND core
    class TRIAGE,INV_AGENTS,DRIFT_AGENT,AUDIT_AGENT agent
    class DB,LLM ext
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/withdrawals/investigate` | Main fraud pipeline |
| GET | `/api/payout/queue` | Officer review queue |
| POST | `/api/payout/decision` | Officer decision |
| POST | `/api/query/chat` | Analyst chat (natural language) |
| POST | `/api/cards/lockdown` | Fraud ring card lockdown |
| POST | `/api/background-audits/trigger` | Trigger background audit run |
| GET | `/api/background-audits/runs/{run_id}/drift-pdf` | Download weight drift PDF report |
| POST | `/api/customers/{id}/weights/pin` | Pin/unpin an indicator weight |

## Performance

| Traffic | Latency | LLM Calls |
|---------|---------|-----------|
| Clean (56%) | 0.14s | 0 |
| Suspicious (44%) | 12.1s | 2-3 |
| Blended | ~2.8s | - |
| Background Audit | 75-220s | 3-10 |
