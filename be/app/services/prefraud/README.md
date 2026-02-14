# Prefraud Service

Always-on customer risk posture computation and fraud pattern detection. Implements two parallel systems: real-time risk scoring via 6 behavioral signals, and periodic pattern discovery via 5 specialized detectors with intelligent deduplication.

## Overview

**PostureService** computes a customer's baseline fraud risk via weighted signal analysis (0.0-1.0 score) and persists snapshots to `customer_risk_posture` table. **PatternDetectionService** discovers fraud patterns (rings, card testing, velocity bursts) from confirmed transactions, deduplicates via Jaccard similarity, and escalates novel patterns to investigation queue.

Both services are scheduler-driven (periodic) and event-driven (on-demand) and follow an async-only, session-per-operation pattern.

## Files

| File | Role | Key Functions/Classes |
|------|------|---|
| `posture_service.py:78` | Posture orchestration | `PostureService.recompute(customer_id, trigger)` → `CustomerRiskPosture` |
| `posture_service.py:155` | Bulk recomputation | `PostureService.recompute_all(trigger)` → list of postures |
| `posture_scheduler.py:49` | Background task | `start_posture_scheduler()` → asyncio.Task |
| `posture_scheduler.py:55` | Event-driven trigger | `trigger_recompute(service, customer_id, trigger)` |
| `detection_service.py:64` | Pattern detection | `PatternDetectionService.run_detection(trigger)` → `DetectionRunResult` |
| `detection_scheduler.py:49` | Background task | `start_detection_scheduler()` → asyncio.Task |
| `detection_scheduler.py:57` | Event-driven trigger | `trigger_detection(service, trigger)` |
| `detectors/base.py:22` | Detector protocol | `PatternDetector` interface, `PatternMatchResult` dataclass |
| `detectors/card_testing.py:13` | Card testing | Detects failed deposit sequences followed by successful withdrawal |
| `detectors/velocity_burst.py:13` | Velocity burst | 4+ withdrawals within 1-hour sliding window |
| `detectors/shared_device_ring.py` | Device ring | Co-location fraud rings via device fingerprints |
| `detectors/rapid_funding_cycle.py` | Funding cycle | Deposit → trading → withdrawal in <6 hours |
| `detectors/no_trade_withdrawal.py` | No-trade | Deposits without trading followed by quick withdrawal |
| `signals/base.py:86` | Signal framework | `SignalResult`, `compute_composite()`, `map_posture()` |
| `signals/payment_risk.py:25` | Payment risk | Method churn, failures, unverified methods (0.95 max) |
| `signals/funding_behavior.py` | Funding patterns | Deposit frequency, size trends |
| `signals/velocity_trends.py` | Withdrawal velocity | 1h/24h/7d withdrawal count escalation |
| `signals/account_maturity.py` | Account age | Tenure-based risk (young accounts higher risk) |
| `signals/infrastructure_stability.py` | IP/device/geo | Churn in infrastructure, impossible travel |
| `signals/graph_proximity.py` | Known fraud graph | Relationship distance to confirmed fraud accounts |
| `signals/pattern_match.py` | Historical overlap | Account overlap with existing fraud patterns |

## Data Flow

### Posture Computation (Real-Time)

```
trigger_recompute(customer_id)
  ↓
PostureService.recompute()
  ├─ Debounce check (skip if <30s since last compute)
  ├─ run_all_signals() → parallel asyncio.gather()
  │  ├─ AccountMaturitySignal.compute() → SignalResult
  │  ├─ VelocityTrendsSignal.compute() → SignalResult
  │  ├─ InfrastructureSignal.compute() → SignalResult
  │  ├─ FundingBehaviorSignal.compute() → SignalResult
  │  ├─ PaymentRiskSignal.compute() → SignalResult
  │  └─ GraphProximitySignal.compute() → SignalResult
  ├─ compute_composite(signals) → weighted average
  ├─ map_posture(score) → "normal"|"watch"|"high_risk"
  └─ save_snapshot(CustomerRiskPosture)
     ↓
     Return detached snapshot (customer_risk_posture table)
```

**Scoring**: Each signal returns 0.0 (safe) to 1.0 (risky). Composite = GLOBAL_MULTIPLIER × Σ(score × weight) / Σ(weight). Weights: {account_maturity: 1.0, velocity_trends: 1.2, infrastructure: 1.3, funding: 1.5, payment: 1.1, graph: 1.4, pattern_match: 1.4}.

**Thresholds**: < 0.30 = normal, < 0.60 = watch, >= 0.60 = high_risk.

### Pattern Detection (Periodic + Event-Driven)

```
trigger_detection(trigger="event:fraud_confirmed")
  ↓
PatternDetectionService.run_detection()
  ├─ Run all 5 detectors in parallel (asyncio.gather, error isolation)
  │  ├─ CardTestingDetector.detect() → list[PatternMatchResult]
  │  ├─ VelocityBurstDetector.detect() → list[PatternMatchResult]
  │  ├─ SharedDeviceRingDetector.detect() → list[PatternMatchResult]
  │  ├─ RapidFundingCycleDetector.detect() → list[PatternMatchResult]
  │  └─ NoTradeWithdrawalDetector.detect() → list[PatternMatchResult]
  ├─ Group by (pattern_type, group_key)
  └─ For each group:
     ├─ Compute Jaccard(new_customers, existing_customers)
     ├─ Jaccard >= 0.8 → skip duplicate, update last_matched_at
     ├─ Jaccard 0.3-0.8 → update existing pattern, add new matches
     └─ Jaccard < 0.3 → create new CANDIDATE FraudPattern + PatternMatches
        ↓
        Persist (fraud_pattern, pattern_match tables)
```

**Deduplication**: Jaccard = |intersection| / |union| of customer IDs. Threshold 0.8 prevents duplicate escalations; 0.3-0.8 merges evolved patterns; <0.3 creates new candidate.

## Key Concepts

**Signal Score**: 0.0 (safe, e.g., 90-day-old account) to 1.0 (risky, e.g., 1-day-old account). Linear interpolation between safe/risky boundaries.

**Composite Score**: Weighted average of all 6 signals. Maps to posture state (normal < 0.30, watch < 0.60, high_risk >= 0.60).

**Pattern Match Result**: {customer_id, confidence, evidence, group_key}. Confidence is 0.0-1.0; evidence is detector-specific (e.g., failed_attempt_count, success_then_withdrawal). Group_key identifies related matches (e.g., device ID for ring patterns).

**Jaccard Deduplication**: Prevents duplicate pattern escalations. High overlap (>= 0.8) = existing pattern, partial overlap (0.3-0.8) = evolved pattern, low overlap (< 0.3) = new pattern.

**Debounce**: Skip recompute if last snapshot < 30s old. Prevents unnecessary recomputation during high-volume event streams.

## Architecture Rules

1. **Async-only**: All DB access via `AsyncSessionLocal` from engine.py (asyncpg driver)
2. **Session per operation**: Each service call opens, uses, and closes own session
3. **Error isolation**: Detectors/signals failing don't cancel others; exceptions logged
4. **Detached entities**: Return Pydantic schemas or detached ORM objects, not in-session objects
5. **No monolithic services**: Split detection into 5 detectors; signals into 7 modules

## Configuration

- `POSTURE_RECOMPUTE_INTERVAL_S`: 3600 (scheduled background loop interval)
- `POSTURE_DEBOUNCE_S`: 30 (skip if last compute < N seconds ago)
- `PATTERN_DETECTION_INTERVAL_S`: 43200 (12 hours, scheduled background loop interval)

## Testing

Validation via `scripts/benchmark_investigate.py` and integration tests. No pytest; test via:
```bash
python -m scripts.seed_data  # Seed 16 test customers
python scripts/benchmark_investigate.py  # Run full pipeline benchmark
```

Expected posture distribution: normal (50-60%), watch (20-30%), high_risk (10-20%) for realistic customer base.
