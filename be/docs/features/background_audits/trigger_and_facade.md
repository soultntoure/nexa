# 01 — Trigger & Facade (Entry Point)

Client hits the API, facade creates an `AuditRun` and spawns the background pipeline.

## Component Diagram

```mermaid
graph LR
    subgraph "API"
        R[background_audits.py :28<br/>POST /trigger]
    end

    subgraph "Service"
        F[facade.py :42<br/>trigger_run]
        P[facade.py :80<br/>_run_pipeline]
    end

    subgraph "Core"
        RW[run_window.py :33<br/>compute_window]
        RF[run_window.py :27<br/>compute_run_fingerprint]
    end

    subgraph "Data"
        RR[audit_run_repository.py<br/>get_by_idempotency_key, create]
    end

    subgraph "External"
        PG[(PostgreSQL<br/>audit_runs)]
    end

    R -->|"lookback_days, mode"| F
    F --> RW & RF
    F -->|"check duplicate"| RR
    RR --> PG
    F -->|"asyncio.create_task"| P
```

## Files Involved

| File | Lines | Key | Line |
|------|-------|-----|------|
| `app/api/routes/background_audits.py` | 79 | `trigger_run` endpoint | 28 |
| `app/services/background_audit/facade.py` | 231 | `BackgroundAuditFacade` class | 37 |
| | | `trigger_run()` | 65 |
| | | `_run_pipeline()` | 103 |
| | | `_build_agent_tools()` → returns `(tools, schema_docs)` | 205 |
| `app/core/background_audit/run_window.py` | 47 | `RunWindow` dataclass | 12 |
| | | `generate_run_id()` | 20 |
| | | `compute_window()` | 33 |
| | | `compute_run_fingerprint()` | 27 |
| `app/data/db/repositories/audit_run_repository.py` | — | `get_by_idempotency_key`, `update_status` | — |
| `app/data/db/models/audit_run.py` | 62 | `AuditRun` model | 34 |

## What Happens

1. Client sends `POST /trigger {lookback_days: 7}`
2. `trigger_run()` computes a `RunWindow` and idempotency key
3. Checks DB for duplicate — returns existing `run_id` if found
4. Creates `AuditRun` record (status=`"pending"`)
5. Spawns `_run_pipeline()` as background task via `asyncio.create_task`
6. Returns `run_id` immediately (HTTP 202)

`_run_pipeline` then calls 4 components sequentially: extract → embed_cluster → candidates → artifacts.

**Schema injection**: `_build_agent_tools()` builds a live schema description from the DB using `build_schema_description()` + `build_critical_notes()` and returns it alongside the tools. The schema is injected into the agent's `SYNTHESIS_PROMPT` at runtime, replacing the `## Database Schema (exact columns)` marker.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API as Routes<br/>background_audits.py
    participant Facade as BackgroundAuditFacade<br/>facade.py:33
    participant DB as PostgreSQL

    Client->>API: POST /background-audits/trigger
    API->>Facade: trigger_run(lookback_days, mode)
    Facade->>DB: Check idempotency key
    Facade->>DB: INSERT audit_runs (status=pending)
    Facade-->>API: run_id (immediate return)
    API-->>Client: 202 {run_id}

    Note over Facade: asyncio.create_task(_run_pipeline)

    Facade->>Facade: _run_pipeline (background)
    Note right of Facade: Phase 1: Extract<br/>Phase 2: Embed+Cluster<br/>Phase 3: Candidates<br/>Phase 4: Artifacts

    Facade->>DB: UPDATE audit_runs status=completed

    Client->>API: GET /runs/{run_id}
    API->>Facade: get_run_status(run_id)
    Facade->>DB: SELECT audit_runs
    API-->>Client: {status: completed, counters, timings}

    Client->>API: GET /runs/{run_id}/candidates
    API->>Facade: get_candidates(run_id)
    Facade->>DB: SELECT audit_candidates
    API-->>Client: [{candidate_id, title, quality_score, pattern_card}]
```
