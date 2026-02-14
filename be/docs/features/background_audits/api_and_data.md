# API Endpoints and Data Models

## Endpoints

**File**: `app/api/routes/background_audits.py`

| Method | Path | Handler Line | Purpose |
|--------|------|-------------|---------|
| POST | `/background-audits/trigger` | :28 | Start a new audit run |
| GET | `/background-audits/runs` | :37 | List all runs (paginated) |
| GET | `/background-audits/runs/{run_id}` | :46 | Get run status + counters |
| GET | `/background-audits/runs/{run_id}/candidates` | :57 | List candidates for a run |
| POST | `/background-audits/candidates/{candidate_id}/action` | :69 | Accept/reject/ignore |

### Trigger Request

```json
POST /background-audits/trigger
{
  "lookback_days": 7,
  "run_mode": "full"
}
// Response: 202 { "run_id": "audit_20260211_...", "status": "pending" }
```

### Candidate Response

```json
GET /runs/{run_id}/candidates
[{
  "candidate_id": "audit_20260211_..._cluster_0",
  "title": "Financial Behavior: Deposit & Run + Shared Device",
  "quality_score": 0.62,
  "confidence": 0.79,
  "support_events": 15,
  "support_accounts": 4,
  "novelty_status": "new",
  "status": "pending",
  "pattern_card": {
    "pattern_type": "financial_behavior",
    "summary": "Cluster of new accounts depositing via card...",
    "indicators": ["no_trade_withdrawal", "shared_device_fingerprint"],
    "agent_report": {
      "plain_language": "...",
      "analyst_notes": "...",
      "limitations": "...",
      "uncertainty": "..."
    },
    "affected_customers": ["CUST-011", "CUST-012"],
    "recommended_action": "Block all 4 accounts..."
  }
}]
```

---

## Database Models

### `audit_runs` — Pipeline execution record

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | |
| `run_id` | str (unique) | `"audit_YYYYMMDD_HHMMSS_<uuid8>"` |
| `status` | str | pending → running → completed/failed |
| `run_mode` | str | "full" or "incremental" |
| `config_snapshot` | JSONB | Frozen config at run start |
| `counters` | JSONB | `{units_extracted, clusters_found, candidates_generated}` |
| `timings` | JSONB | `{extract, embed_cluster, candidate_report, artifact_write}` |
| `idempotency_key` | str (unique) | SHA256(window + mode) — prevents duplicate runs |

### `audit_text_units` — Extracted reasoning units

| Column | Type | Notes |
|--------|------|-------|
| `unit_id` | str (unique) | Deterministic: SHA256(eval_id\|source\|idx) |
| `evaluation_id` | UUID (FK) | Source evaluation |
| `source_type` | str | "triage" or "investigator" |
| `source_name` | str | "constellation_analysis" or investigator name |
| `text_masked` | text | PII-masked reasoning |
| `text_hash` | str | SHA256(masked_text) for dedup |
| `vector_status` | str | "pending" → "embedded" |

### `audit_candidates` — Discovered fraud patterns

| Column | Type | Notes |
|--------|------|-------|
| `candidate_id` | str (unique) | `"{run_id}_{cluster_id}"` |
| `run_id` | str | FK to audit_runs |
| `quality_score` | float | Weighted formula (see scoring doc) |
| `confidence` | float | Avg investigator confidence |
| `support_events` | int | Count of text units |
| `support_accounts` | int | Count of distinct withdrawals |
| `novelty_status` | str | "new", "drifted_existing", "existing" |
| `pattern_card` | JSONB | Full pattern details + agent report |
| `status` | str | "pending" → "accepted"/"rejected"/"ignore" |

### `audit_candidate_evidence` — Link table

| Column | Type | Notes |
|--------|------|-------|
| `candidate_id` | str (FK) | Links to audit_candidates |
| `unit_id` | str | Links to audit_text_units |
| `rank` | int | 0 = strongest evidence |
| `snippet` | text | First 200 chars preview |

---

## JSONB: `pattern_card` Schema

```
{
  "pattern_type": "financial_behavior" | "identity_access" | "cross_account",
  "summary": "Plain text description of the pattern",
  "indicators": ["no_trade_withdrawal", "shared_device_fingerprint", ...],
  "agent_report": {
    "plain_language": "Admin-facing narrative (LLM-generated)",
    "analyst_notes": "Technical notes for fraud team",
    "limitations": "Known limitations of this detection",
    "uncertainty": "Areas where confidence is low"
  },
  "affected_customers": ["CUST-011", "CUST-012"],
  "recommended_action": "Suggested next step"
}
```

The `agent_report` field is populated by `BackgroundAuditAgent.synthesize_candidate()` using the `SYNTHESIS_PROMPT` (Gemini 2.0 Flash, temp=0.1).
