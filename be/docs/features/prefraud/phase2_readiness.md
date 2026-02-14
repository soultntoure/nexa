# Phase 2 Readiness — What the Posture Engine Enables

Phase 1 delivers a working posture engine with 6 SQL-based signals, API endpoints, background scheduling, event-driven triggers, and investigation pipeline integration. This document outlines what Phase 2 builds on.

---

## What Phase 1 Delivers to Phase 2

### 1. Structured Signal Data for Pattern Detection Features

Every posture snapshot persists both `signal_scores` (6 numeric features) and `signal_evidence` (rich structured data per signal). Phase 2 pattern detectors can reference these to identify candidates for deeper analysis.

```json
{
    "account_maturity": 0.72,
    "velocity_trends": 0.83,
    "infrastructure_stability": 0.25,
    "funding_behavior": 0.70,
    "payment_risk": 0.24,
    "graph_proximity": 0.73
}
```

Each signal score is a pre-normalized 0.0-1.0 feature ready for candidate selection.

### 2. Candidate Selection for Pattern Detection

Customers flagged `watch` or `high_risk` are natural candidates for deeper pattern analysis. Phase 2 can query:

```sql
SELECT customer_id, signal_scores, signal_evidence
FROM customer_risk_postures
WHERE is_current = TRUE AND posture IN ('watch', 'high_risk')
```

This focuses expensive pattern detection on the customers most likely to exhibit fraud patterns.

### 3. Graph Foundation for Multi-Hop Analysis

The `graph_proximity` signal detects direct entity sharing. Its evidence includes:

- `shared_device_customers` / `shared_ip_customers` / `shared_recipient_customers` — direct connections
- `second_degree_exposure` — count of second-degree connections (logged but not scored in Phase 1)
- `detection_scope: "direct_entity_sharing_only"` — explicit scope tag

Phase 2 extends this to multi-hop graph traversal via PostgreSQL recursive CTEs, using the second-degree exposure data as a starting point.

### 4. Event Infrastructure for Real-Time Pattern Detection

The event trigger system (5 trigger points) fires posture recomputes within seconds of key account actions. Phase 2 can:

- Extend these triggers to also fire pattern detection on fraud confirmation
- Use the same `trigger_recompute()` pattern for pattern-aware posture updates
- Add Signal #7 (pattern_match) to the existing parallel signal pipeline

### 5. Temporal History for Trend Analysis

Every posture computation is saved as a full snapshot with timestamps. Phase 2 can analyze posture trajectories:

- Customers transitioning from `normal` to `watch` (emerging risk)
- Customers oscillating between states (behavioral inconsistency)
- Rate of composite score change over time (acceleration detection)

```sql
SELECT customer_id, composite_score, computed_at
FROM customer_risk_postures
WHERE customer_id = $1
ORDER BY computed_at DESC
LIMIT 30
```

---

## Phase 2 Signal Enhancement: Signal #7 (pattern_match)

Phase 2 adds a 7th signal to the posture pipeline that reads pre-computed pattern matches from the `pattern_matches` junction table. This signal:

- **Weight**: 1.4 (same as graph_proximity)
- **Score**: max(match.confidence) for active pattern matches, capped at 0.85
- **Cost**: single indexed read (~1ms)
- **Gated by**: `PATTERN_SCORING_ENABLED` config flag (default: false = shadow mode)

The total weight sum increases from 7.5 to 8.9. The composite formula remains the same pattern:

```
composite = GLOBAL_MULTIPLIER * sum(signal_score * weight) / sum(weight)
```

---

## Graph Proximity: Multi-Hop Extension

Phase 1 detects only direct sharing (customer A and B share the same device/IP/recipient). Phase 2 extends to:

- **2-hop connections**: A shares device with B, B shares IP with C — A and C are connected
- **Fraud ring clustering**: Groups of 3+ customers sharing multiple entity types
- **Temporal correlation**: Shared entities used within similar time windows

Implementation: PostgreSQL recursive CTEs with `CYCLE` clause (depth guard: max 4 hops). No new dependencies — extends the existing SQL-only approach.

---

## Configuration Flags for Gradual Rollout

Phase 1 provides configuration controls for safe activation:

| Flag | Phase 1 Default | Phase 2 Addition |
|---|---|---|
| `POSTURE_INFLUENCE_ENABLED` | `false` | Set `true` when confident in calibration |
| `MAX_POSTURE_UPLIFT` | `0.15` | Adjust based on false-positive analysis |
| `POSTURE_UPLIFT_WEIGHT` | `0.3` | Tune based on feedback loop outcomes |
| `POSTURE_RECOMPUTE_INTERVAL_S` | `3600` | Decrease for faster response |
| `POSTURE_DEBOUNCE_S` | `5` | Adjust for event burst handling |
| `PATTERN_DETECTION_ENABLED` | — | `true` (enable detection job) |
| `PATTERN_SCORING_ENABLED` | — | `false` (shadow mode for Signal #7) |
| `PATTERN_DETECTION_INTERVAL_S` | — | `43200` (12 hours) |

### Recommended Activation Sequence

1. **Observe shadow mode** — Monitor posture distributions and top reasons across the customer base
2. **Validate against known outcomes** — Compare posture predictions with historical fraud decisions
3. **Enable posture influence** — `POSTURE_INFLUENCE_ENABLED=true`, `MAX_POSTURE_UPLIFT=0.05`
4. **Deploy pattern detection** — Detectors run, matches stored, Signal #7 stays at 0.0
5. **Enable pattern scoring** — `PATTERN_SCORING_ENABLED=true` after pattern precision validated
6. **Gradually increase influence** — Raise uplift cap as confidence grows from feedback data

---

## Data Available for Phase 2

| Data Source | Table | Key Fields for Pattern Detection |
|---|---|---|
| Posture snapshots | `customer_risk_postures` | signal_scores (6 features), composite_score, posture state |
| Signal evidence | `customer_risk_postures.signal_evidence` | Per-signal structured data (account age, velocity ratios, device counts, etc.) |
| Posture history | `customer_risk_postures` (all rows) | Temporal trajectory, trigger sources |
| Customer profiles | `customers` | Registration date, is_flagged, external_id |
| Transaction patterns | `transactions` | Amounts, frequencies, failure rates |
| Device/IP patterns | `devices`, `ip_history` | Fingerprints, locations, VPN flags |
| Payment methods | `payment_methods` | Verification status, blacklist flags |
| Investigation outcomes | `evaluations.investigation_data` | Posture context at decision time |
