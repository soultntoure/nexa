# 03 — Embed & Cluster (Phase 2)

Turns text units into vectors, stores them in ChromaDB, clusters with HDBSCAN.

## Component Diagram

```mermaid
graph LR
    subgraph "Service"
        EC[embed_cluster.py :35<br/>embed_and_cluster]
    end

    subgraph "Core"
        CA[cluster_assigner.py :24<br/>assign_clusters — HDBSCAN]
        CC[cluster_assigner.py :83<br/>compute_centroid]
        ND[novelty_detector.py :22<br/>detect_novelty]
    end

    subgraph "Data"
        UR[audit_unit_repository.py<br/>mark_vector_status]
    end

    subgraph "External"
        GM[Gemini Embedding API<br/>768-dim vectors]
        CH[(ChromaDB<br/>vector store)]
        PG[(PostgreSQL)]
    end

    EC -->|"text_masked list"| GM
    GM -->|"768-dim embeddings"| EC
    EC -->|"upsert vectors"| CH
    EC -->|"mark embedded"| UR --> PG
    EC -->|"embeddings array"| CA
    CA -->|"cluster labels"| EC
    EC --> CC --> ND
```

## Files Involved

| File | Lines | Key | Line |
|------|-------|-----|------|
| `app/services/background_audit/components/embed_cluster.py` | 86 | `ClusterData` dataclass | 25 |
| | | `embed_and_cluster()` | 35 |
| `app/core/background_audit/cluster_assigner.py` | 95 | `assign_clusters()` | 24 |
| | | `compute_centroid()` | 83 |
| `app/core/background_audit/novelty_detector.py` | 55 | `NoveltyResult` dataclass | 13 |
| | | `detect_novelty()` | 22 |

## What Happens

1. Embed all `text_masked` strings via Gemini (`gemini-embedding-001`, 768 dims)
2. Upsert vectors + metadata to ChromaDB
3. Mark `vector_status = "embedded"` in PostgreSQL
4. Run HDBSCAN: `min_cluster_size=5, metric=euclidean, method=eom`
   - Label `-1` = noise → discarded
5. For each cluster:
   - `compute_centroid()` — `np.mean(embeddings, axis=0)`
   - `detect_novelty()` — cosine sim vs existing centroids:
     - ≥0.82 → `"existing"`, 0.70–0.82 → `"drifted_existing"`, <0.70 → `"new"`
     - Currently always `"new"` (no prior centroids stored yet)

**Output**: `list[ClusterData(cluster_id, units, centroid, novelty)]`

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Facade as facade.py:97
    participant EC as embed_cluster.py:35
    participant Gemini as Gemini Embedding API
    participant Chroma as ChromaDB
    participant CA as cluster_assigner.py:24
    participant ND as novelty_detector.py:22
    participant UnitRepo as audit_unit_repository.py

    Facade->>EC: embed_and_cluster(units, session_factory)

    EC->>Gemini: embed_texts([unit.text_masked for unit in units])
    Note right of Gemini: Model: gemini-embedding-001<br/>Output: 768-dim vectors
    Gemini-->>EC: list[list[float]] (768-dim each)

    EC->>Chroma: upsert_vectors(unit_ids, embeddings, metadatas)
    EC->>UnitRepo: mark_vector_status(unit_ids, "embedded")

    EC->>CA: assign_clusters(embeddings)
    Note right of CA: HDBSCAN<br/>min_cluster_size=5<br/>metric=euclidean<br/>method=eom
    CA-->>EC: ClusterResult(labels, n_clusters, noise_count)

    loop For each cluster (skip noise label -1)
        EC->>CA: compute_centroid(cluster_embeddings) → np.mean
        EC->>ND: detect_novelty(centroid, existing_centroids={})
        Note right of ND: Cosine sim thresholds:<br/>≥0.82 → existing<br/>0.70-0.82 → drifted<br/><0.70 → new
        ND-->>EC: NoveltyResult(status="new")
    end

    EC-->>Facade: list[ClusterData(cluster_id, units, centroid, novelty)]
```
