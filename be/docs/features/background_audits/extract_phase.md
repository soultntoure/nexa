# 02 — Extract Cohort (Phase 1)

Pulls reasoning text from confirmed-fraud evaluations, normalizes it, and deduplicates.

## Component Diagram

```mermaid
graph LR
    subgraph "Service"
        EX[extract.py :24<br/>extract_cohort]
    end

    subgraph "Core"
        CF[cohort_filter.py :18<br/>build_cohort_query]
        RU[cohort_filter.py :35<br/>extract_reasoning_units]
        TN[text_normalizer.py<br/>normalize :15, mask_pii :22, validate :30]
        HP[hash_policy.py<br/>text_hash :8, unit_id :13]
    end

    subgraph "Data"
        UR[audit_unit_repository.py<br/>get_existing_hashes, bulk_upsert]
    end

    subgraph "External"
        PG[(PostgreSQL<br/>evaluations, withdrawals<br/>→ audit_text_units)]
    end

    EX --> CF -->|"SQL query"| PG
    PG -->|"list[Evaluation]"| EX
    EX --> RU
    RU -->|"raw text units"| TN
    TN --> HP
    HP -->|"dedup check"| UR
    UR -->|"upsert new units"| PG
```

## Files Involved

| File | Lines | Key | Line |
|------|-------|-----|------|
| `app/services/background_audit/components/extract.py` | 74 | `extract_cohort()` | 24 |
| `app/core/background_audit/cohort_filter.py` | 81 | `build_cohort_query()` | 18 |
| | | `extract_reasoning_units()` | 35 |
| `app/core/background_audit/text_normalizer.py` | 38 | `normalize_text()` | 15 |
| | | `mask_pii()` | 22 |
| | | `validate_quality()` | 30 |
| `app/core/background_audit/hash_policy.py` | 19 | `compute_text_hash()` | 8 |
| | | `compute_unit_id()` | 13 |
| `app/data/db/repositories/audit_unit_repository.py` | — | `bulk_upsert_units`, `get_existing_hashes` | — |
| `app/data/db/models/audit_text_unit.py` | — | `AuditTextUnit` model | — |

## What Happens

1. `build_cohort_query()` builds a SQLAlchemy select:
   ```
   SELECT evaluations JOIN withdrawals
   WHERE is_fraud = True AND checked_at IN window
   ```
2. For each evaluation, `extract_reasoning_units()` parses `investigation_data` JSONB:
   - `triage.constellation_analysis` → 1 text unit
   - `investigators[].reasoning` → 1 text unit per investigator
3. Each raw text goes through the processing pipeline:
   - `normalize_text()` — collapse whitespace, strip control chars
   - `mask_pii()` — emails→`[EMAIL]`, IPs→`[IP]`, accounts→`[ACCT]`
   - `validate_quality()` — reject if <20 chars, >5000 chars, or <5 words
4. `compute_text_hash()` — SHA256 of masked text (dedup key)
5. `compute_unit_id()` — SHA256 of `eval_id|source_type|index` (deterministic ID)
6. Check existing hashes in DB, bulk-upsert only new units

**Output**: `list[AuditTextUnit]` (deduplicated, PII-masked)

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Facade as facade.py:93
    participant Extract as extract.py:24
    participant Cohort as cohort_filter.py:18
    participant Norm as text_normalizer.py
    participant Hash as hash_policy.py
    participant DB as PostgreSQL
    participant UnitRepo as audit_unit_repository.py

    Facade->>Extract: extract_cohort(window, session_factory)
    Extract->>Cohort: build_cohort_query(start, end)
    Note right of Cohort: SELECT evaluations<br/>JOIN withdrawals<br/>WHERE is_fraud=True<br/>AND checked_at in window
    Cohort-->>Extract: SQLAlchemy stmt

    Extract->>DB: execute(stmt)
    DB-->>Extract: list[Evaluation] with investigation_data

    loop For each Evaluation
        Extract->>Cohort: extract_reasoning_units(eval_id, wd_id, investigation_data)
        Note right of Cohort: Parse triage.constellation_analysis<br/>Parse investigators[].reasoning
        Cohort-->>Extract: list[{source_type, text, score, confidence}]
    end

    loop For each reasoning unit
        Extract->>Norm: normalize_text(text)
        Extract->>Norm: mask_pii(text) → [EMAIL] [IP] [ACCT]
        Extract->>Norm: validate_quality(text) → min 20 chars, 5 words
        Extract->>Hash: compute_text_hash(masked_text) → SHA256
        Extract->>Hash: compute_unit_id(eval_id, source_type, idx) → SHA256[:32]
    end

    Extract->>UnitRepo: get_existing_hashes() → set[str]
    Note right of Extract: Filter duplicates by text_hash
    Extract->>UnitRepo: bulk_upsert_units(new_units)
    Extract-->>Facade: list[AuditTextUnit]
```
