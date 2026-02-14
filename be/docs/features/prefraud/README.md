# Pre-Fraud Posture Engine V1

> Phase 0+1 Implementation -- Always-on customer risk posture, precomputed and available instantly at payout time.

## What It Is

The Pre-Fraud Posture Engine continuously computes a risk state (`normal` / `watch` / `high_risk`) per customer, independent of any specific withdrawal request. Unlike the rule engine which evaluates risk at payout time, posture is precomputed from historical behavior patterns and updated both on schedule and in response to account events.

## Why It Matters

The existing fraud detection pipeline evaluates risk only when a withdrawal is submitted. This creates a blind spot: a customer can accumulate suspicious behavior (rapid deposits, device churn, shared infrastructure with known fraudsters) for days before any check runs. The posture engine closes this gap by continuously monitoring 6 behavioral signal families and maintaining an always-current risk snapshot.

## Architecture

```
                    +------------------+
                    |   Event Triggers |
                    | (new device, IP, |
                    |  method, WD, tx) |
                    +--------+---------+
                             |
                    fire-and-forget
                             |
                             v
+------------------+   +----+----------+   +-----------------+
| Scheduled Loop   +-->| PostureService |-->| PostureRepo     |
| (hourly default) |   |  .recompute() |   |  .save_snapshot()|
+------------------+   +----+----------+   +---------+-------+
                             |                        |
                    +--------v--------+      +--------v--------+
                    | run_all_signals |      | customer_risk_  |
                    | (6 in parallel) |      | postures table  |
                    +--------+--------+      +-----------------+
                             |
              +--------------+---------------+
              |       |       |       |      |       |
              v       v       v       v      v       v
          account  velocity  infra  funding payment graph
          maturity trends   stabil. behavior risk   proximity
```

### Data Flow

1. **Trigger** -- Either the hourly scheduler or an account event fires a recompute
2. **Signal Computation** -- All 6 signals run in parallel, each opening its own DB session
3. **Composite Scoring** -- Weighted average of signal scores maps to a posture state
4. **Persistence** -- Full snapshot (scores + evidence + reasons) saved to `customer_risk_postures`
5. **Consumption** -- Investigation pipeline reads the latest snapshot at payout time

### Integration with Investigation Pipeline

Posture integrates at two levels:

- **Score Uplift** (gated by `POSTURE_INFLUENCE_ENABLED`, default `false`): Adds up to 0.15 to the rule engine composite score for `watch`/`high_risk` customers
- **Triage Context** (always active): Injects posture state and top reasons into the LLM triage prompt for richer decision-making

## Posture States

| State | Composite Score | Meaning |
|---|---|---|
| `normal` | < 0.30 | No significant risk signals. Standard processing. |
| `watch` | 0.30 -- 0.59 | Elevated risk. Monitored, context injected into triage. |
| `high_risk` | >= 0.60 | Significant risk across multiple signals. Priority review. |

## Signal Families

| Signal | Weight | What It Detects |
|---|---|---|
| Account Maturity | 1.0 | New, inactive, or recently-reactivated accounts |
| Velocity Trends | 1.2 | Acceleration in deposits/withdrawals vs baseline |
| Infrastructure Stability | 1.3 | Device churn, IP instability, VPN usage |
| Funding Behavior | 1.5 | Deposit-and-run patterns, funding/trading imbalance |
| Payment Risk | 1.1 | Method churn, unverified methods, failed transactions |
| Graph Proximity | 1.4 | Shared infrastructure with other customers |

See [signal_reference.md](signal_reference.md) for detailed scoring formulas and thresholds.

## Composite Scoring

```
composite = GLOBAL_MULTIPLIER * sum(signal_score * weight) / sum(weight)
```

- `GLOBAL_MULTIPLIER = 1.0`
- Total weight = 1.0 + 1.2 + 1.3 + 1.5 + 1.1 + 1.4 = **7.5**
- Each signal scores 0.0 (safe) to 1.0 (risky)

## Configuration

| Setting | Default | Description |
|---|---|---|
| `POSTURE_INFLUENCE_ENABLED` | `false` | Shadow mode. Set `true` to enable score uplift at payout. |
| `POSTURE_RECOMPUTE_INTERVAL_S` | `3600` | Scheduled recompute interval (seconds) |
| `POSTURE_DEBOUNCE_S` | `5` | Minimum seconds between recomputes for same customer |
| `MAX_POSTURE_UPLIFT` | `0.15` | Maximum score uplift posture can add at payout |
| `POSTURE_UPLIFT_WEIGHT` | `0.3` | Multiplier: `uplift = min(composite * 0.3, 0.15)` |

## File Structure

### New Files (17)

```
app/data/db/models/customer_risk_posture.py          # ORM model
app/data/db/repositories/posture_repository.py        # CRUD + queries
alembic/versions/c7f8a9b0d1e2_add_customer_risk_postures.py  # Migration

app/services/prefraud/__init__.py
app/services/prefraud/posture_service.py              # Orchestrator
app/services/prefraud/posture_scheduler.py            # Background loop + event triggers

app/services/prefraud/signals/__init__.py             # run_all_signals() registry
app/services/prefraud/signals/base.py                 # SignalResult, weights, thresholds
app/services/prefraud/signals/account_maturity.py
app/services/prefraud/signals/velocity_trends.py
app/services/prefraud/signals/infrastructure_stability.py
app/services/prefraud/signals/funding_behavior.py
app/services/prefraud/signals/payment_risk.py
app/services/prefraud/signals/graph_proximity.py

app/api/routes/prefraud.py                            # REST endpoints
app/api/schemas/posture.py                            # Pydantic response models

scripts/seed_postures.py                              # Validation runner
```

### Modified Files (5)

```
app/main.py                                           # PostureService + scheduler in lifespan
app/config.py                                         # POSTURE_* config vars
app/services/fraud/investigator_service.py            # Parallel posture loading + uplift
app/data/db/models/__init__.py                        # Export CustomerRiskPosture
scripts/seed_data.py                                  # Calls seed_posture_enrichments()
```

## Safety Properties

1. **Shadow mode by default** -- Posture computes and stores but does not affect payout scoring until `POSTURE_INFLUENCE_ENABLED=true`
2. **One-directional uplift** -- Posture can only increase risk, never decrease it
3. **Capped contribution** -- Maximum uplift is 0.15; posture alone cannot cross the 0.70 hard-block threshold
4. **Deterministic hard-stops unaffected** -- Existing rule engine overrides (hard escalation, multi-critical) remain authoritative
5. **Graceful degradation** -- If posture computation fails, the investigation pipeline continues with rule engine only
6. **Full explainability** -- Every posture includes top reasons and full signal evidence
7. **Complete audit trail** -- Full snapshot history with trigger source recorded

## Related Documentation

- [Signal Reference](signal_reference.md) -- Detailed scoring formulas for all 6 signals
- [API Reference](api_reference.md) -- REST endpoints, schemas, example responses
- [Validation Report](validation_report.md) -- Seed data validation results and analysis
- [Phase 2 Readiness](phase2_readiness.md) -- What Phase 2 can build on
