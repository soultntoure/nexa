# Background Audit Service

Pattern discovery pipeline from confirmed-fraud evaluations. Extracts reasoning units, clusters via embeddings + HDBSCAN, investigates with an LLM agent, outputs ranked fraud pattern candidates.

## Pipeline Flow

```mermaid
flowchart TD
    A[POST /api/audit/run] --> B[BackgroundAuditFacade.trigger_run]
    B --> C{Duplicate run?}
    C -- Yes --> D[Return existing run_id]
    C -- No --> E[Create AuditRun + launch async task]

    E --> P1

    subgraph P1 [Phase 1 — Extract]
        F1[Query evaluations WHERE decision = blocked_by_fraud] --> F2[Parse investigation_data JSONB]
        F2 --> F3[Normalize + mask PII + hash dedup]
        F3 --> F4[Upsert AuditTextUnit rows]
    end

    P1 --> P2

    subgraph P2 [Phase 2 — Embed & Cluster]
        G1[Embed text units via ChromaDB API] --> G2[Upsert vectors + mark embedded]
        G2 --> G3[HDBSCAN clustering]
        G3 --> G4[Compute centroids + novelty assessment]
    end

    P2 --> P3

    subgraph P3 [Phase 3 — Investigate & Assemble]
        H1[Filter clusters by quality gate] --> H2[LLM agent investigates each cluster]
        H2 --> H3[Generate pattern cards]
        H3 --> H4[Signature dedup + merge]
        H4 --> H5[Persist audit_candidate + evidence]
    end

    P3 --> Z[AuditRun status = completed]
```

## SSE Event Stream

```mermaid
sequenceDiagram
    participant Client
    participant API as GET /api/audit/progress/{run_id}
    participant Facade

    Client->>API: Connect SSE
    API->>Facade: attach_progress(run_id)

    Facade-->>Client: phase_start (extract)
    Facade-->>Client: progress (N units found)
    Facade-->>Client: phase_start (embed_cluster)
    Facade-->>Client: progress (N clusters found)
    Facade-->>Client: phase_start (investigate)
    Facade-->>Client: hypothesis (agent thinking)
    Facade-->>Client: candidate (pattern found)
    Facade-->>Client: complete (N candidates)
    Facade-->>Client: null (stream end)
```

## Investigation Detail

```mermaid
flowchart LR
    subgraph Quality Gate
        QG[min_events ≥ 5<br/>min_accounts ≥ 2<br/>min_confidence ≥ 0.50]
    end

    CL[Clusters] --> QG
    QG -- pass --> INV[LLM Agent<br/>SQL + Web Search tools]
    QG -- fail --> SKIP[Discarded]

    INV --> PC[Pattern Card<br/>formal_name + plain_language<br/>+ SQL findings + web refs]
    PC --> SIG{Signature match?}
    SIG -- new --> SAVE[Save audit_candidate]
    SIG -- duplicate --> MERGE[Merge with existing]
    SAVE --> EV[Rank & persist evidence]
    MERGE --> EV
```

## File Map

```mermaid
graph LR
    subgraph Orchestration
        FA[facade.py] --> QR[queries.py]
        FA --> PR[progress.py]
    end

    subgraph Phase Components
        EX[extract.py]
        EC[embed_cluster.py]
        CR[candidate_report.py]
        CU[candidate_utils.py]
    end

    subgraph Internals
        CI[candidate_investigation.py]
        CA[candidate_assembly.py]
        CB[candidate_pattern_card_builder.py]
        CM[candidate_support_metrics.py]
        CS[candidate_store.py]
    end

    FA --> EX & EC & CR
    CR --> CI & CA
    CA --> CB & CM & CS
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Reasoning Unit** | Text snippet from `investigation_data` JSONB, normalized + PII-masked + deduped by hash |
| **Cluster** | HDBSCAN group of similar units with centroid vector + novelty status |
| **Pattern Card** | LLM-generated hypothesis: name, explanation, SQL findings, web references |
| **Candidate Signature** | Dedup key from pattern_type + account_ids + amount_range + feature_hash |
| **Novelty Assessment** | Novel vs similar-to-known, based on centroid distance to known clusters |

## Config

| Setting | Default | Description |
|---------|---------|-------------|
| `BACKGROUND_AUDIT_LOOKBACK_DAYS` | 7 | Evaluation window |
| `BACKGROUND_AUDIT_MAX_CANDIDATES` | 50 | Max output candidates |
| `BACKGROUND_AUDIT_CLUSTER_MIN_SIZE` | 8 | HDBSCAN min cluster size |
| `BACKGROUND_AUDIT_CLUSTER_MIN_SAMPLES` | 4 | HDBSCAN min samples |
| `BACKGROUND_AUDIT_CLUSTER_MERGE_SIMILARITY` | 0.90 | Merge threshold |
| `TAVILY_API_KEY` | — | Web search tool (optional) |

DB config overrides env defaults via `_load_run_config()` in `facade.py`.
