# Scoring, Clustering, and Quality Gates

## Quality Gate (Entry Filter)

**File**: `app/core/background_audit/confidence_calculator.py:27`

A cluster must pass all 3 thresholds to become a candidate:

| Criterion | Threshold | Why |
|-----------|-----------|-----|
| `support_events` | ≥ 5 | Meaningful even with small seed data (7+ unit clusters pass) |
| `support_accounts` | ≥ 2 | A pattern involving 2+ accounts is worth investigating |
| `avg_confidence` | ≥ 0.50 | Allow moderate-confidence clusters through for agent synthesis |

Clusters that fail are silently dropped — no DB record created.

> **History**: Thresholds were lowered from 15/5/0.65 to 5/2/0.50 in Stage 2 — the original values filtered out 8 of 9 clusters in seed data runs.

---

## Candidate Quality Score

**File**: `app/core/background_audit/confidence_calculator.py:6`

```
quality = 0.35 × confidence
        + 0.25 × support_score
        + 0.20 × impact_estimate
        + 0.20 × evidence_quality
```

| Term | Calculation |
|------|-------------|
| `confidence` | `mean(unit.confidence for unit in cluster)` |
| `support_score` | `0.6 × min(events/50, 1.0) + 0.4 × min(accounts/20, 1.0)` |
| `impact_estimate` | `0.5` (hardcoded — Phase 2 will calculate from dollar amounts) |
| `evidence_quality` | `mean(unit.score for unit in cluster)` |

---

## Evidence Ranking

**File**: `app/core/background_audit/evidence_ranker.py:8`

Ranks text units within a candidate for display (top 10 shown):

```
rank = 0.4 × confidence + 0.3 × score + 0.3 × diversity_bonus
```

- `diversity_bonus` = 0.1 if first unit from that `withdrawal_id` (rewards breadth over depth)
- Max 10 evidence items per candidate

---

## HDBSCAN Clustering

**File**: `app/core/background_audit/cluster_assigner.py:24`

```python
HDBSCAN(min_cluster_size=5, metric="euclidean", cluster_selection_method="eom")
```

- **Input**: 768-dim Gemini embedding vectors
- **Output**: integer labels per unit (-1 = noise, discarded)
- **Centroid**: `np.mean(cluster_embeddings, axis=0)` (line 83)

---

## Novelty Detection

**File**: `app/core/background_audit/novelty_detector.py:22`

Compares new centroid vs existing centroids via cosine similarity:

| Cosine Sim | Status | Meaning |
|------------|--------|---------|
| ≥ 0.82 | `existing` | Known pattern, already tracked |
| 0.70–0.82 | `drifted_existing` | Evolving variant of known pattern |
| < 0.70 | `new` | Novel, never seen before |

**Current**: `existing_centroids={}` → always returns `"new"`. Will be populated once runs accumulate.

---

## Text Processing Pipeline

**File**: `app/core/background_audit/text_normalizer.py`

```
Raw reasoning → normalize_text → mask_pii → validate_quality → hash
```

| Step | Line | Transforms |
|------|------|------------|
| `normalize_text` | :15 | Collapse `\s+` → ` `, strip control chars |
| `mask_pii` | :22 | Emails → `[EMAIL]`, IPs → `[IP]`, account nums → `[ACCT]` |
| `validate_quality` | :30 | Min 20 chars, max 5000 chars, min 5 words |

**Dedup**: `SHA256(masked_text)` — identical reasoning from different evaluations is only embedded once.

**File**: `app/core/background_audit/hash_policy.py:8`

| Step | Line | Transforms |
|------|------|------------|
| `compute_text_hash` | :8 | SHA256 of masked text (dedup key) |
| `compute_unit_id` | :13 | SHA256 of `eval_id|source_type|index` (deterministic ID) |
