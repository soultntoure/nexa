# Seed Data Pipeline

Deterministic test data pipeline for the pre-fraud posture engine. Seeds 16 customers across 3 risk tiers with temporal depth for all 6 posture signals.

## Quick Start

```bash
# 1. Start the database
docker-compose up db

# 2. Seed base data + enrichments + dashboard
python -m scripts.seed_data

# 3. Seed posture history + compute current postures + validate
python -m scripts.seed_postures
```

## Pipeline Architecture

```
seed_data.py
  |
  |-- Truncate all tables (CASCADE)
  |-- Seed 16 customer scenarios (base profiles)
  |-- seed_posture_enrichments.py  (temporal depth for signals)
  |-- seed_dashboard.py            (evaluations, indicators, alerts)
  |
  v
seed_postures.py  (separate invocation)
  |
  |-- seed_posture_history.py  (96 historical snapshots)
  |-- PostureService.recompute_all()  (compute + persist current postures)
  |-- Validate against expected tiers
```

## Scripts

### 1. seed_data.py — Base Customer Data

**Run:** `python -m scripts.seed_data`

Seeds 16 customers with complete profiles: `Customer`, `PaymentMethod`, `Device`, `IPHistory`, `Transaction`, `Trade`, `Withdrawal`, `CustomerWeightProfile`, `ThresholdConfig`.

| Tier | Customers | Expected Posture |
|------|-----------|-----------------|
| Clean (6) | Sarah Chen, James Wilson, Aisha Mohammed, Kenji Sato, Emma Davies, Raj Patel | `normal` |
| Escalate (4) | David Park, Maria Santos, Tom Brown, Yuki Tanaka | `watch` |
| Fraud (6) | Victor Petrov, Sophie Laurent, Ahmed Hassan, Fatima Nour, Carlos Mendez, Nina Volkov | `high_risk` |

Fraud customers have `is_flagged=True` to activate the `graph_proximity` signal's flagged-connection override (score = 0.9).

Each customer has a pending withdrawal for demo/evaluation purposes.

**Tables truncated before seeding:**

`customer_risk_postures`, `evaluations`, `feedback`, `indicator_results`, `withdrawal_decisions`, `alerts`, `withdrawals`, `trades`, `transactions`, `ip_history`, `devices`, `payment_methods`, `customer_weight_profiles`, `customers`, `threshold_config`, `fraud_patterns`

### 2. seed_posture_enrichments.py — Temporal Depth

**Run:** Called from `seed_data.py` main(), or standalone via `python -m scripts.seed_posture_enrichments`

Adds extra records to existing customers so posture signals produce differentiated results. The base data in `seed_data.py` is optimized for the rule-engine (indicators). Enrichments target the 6 posture signals specifically.

**Clean customers — reinforce stable baselines:**

| Customer | Enrichments | Signal Effect |
|----------|-------------|---------------|
| Sarah | 4 extra deposits (25d, 18d, 120d, 300d) | velocity_trends: stable 7d/baseline ratio |
| James | 3 extra deposits (20d, 12d, 8d) | velocity_trends: strong baseline prevents false spike |
| Aisha | 4 deposits + 1 IP (120d) | funding_behavior: healthy deposit-to-trade ratio |
| Kenji | 3 deposits + 1 IP (45d) | funding_behavior: consistent crypto pattern |
| Emma | 5 deposits + 10 trades + 1 IP (400d) | velocity_trends + account_maturity: veteran baseline |
| Raj | 3 deposits + 1 IP (200d) | funding_behavior: premium trader baseline |

**Escalate customers — inject specific signal anomalies:**

| Customer | Enrichments | Signal Effect |
|----------|-------------|---------------|
| David | 4 IPs (SGP, VPN DEU, THA, VPN BRA) + 3 VPN deposits | infrastructure_stability: countries + VPN ratio spike |
| Maria | 3 rapid deposits + 1 failed tx + 1 unverified e-wallet | velocity_trends + payment_risk: new account velocity |
| Tom | 3 failed crypto txns + 2 rapid deposits | payment_risk: failed_tx_rate + velocity spike |
| Yuki | 5 pre-dormancy trades + 3 pre-dormancy deposits + 3 return deposits | velocity_trends: post-dormancy spike vs zero baseline |

**Fraud customers — amplify fraud patterns:**

| Customer | Enrichments | Signal Effect |
|----------|-------------|---------------|
| Victor | 3 rapid deposits ($6k) + fraud ring IP | velocity_trends: 900:1 deposit-to-trade + graph_proximity |
| Sophie | 2 failed cards + 2 VPN deposits + VPN IP | payment_risk: high failure rate + infrastructure instability |
| Ahmed/Fatima | 3 coordinated deposit pairs + shared IP | graph_proximity: multi-signal fraud ring evidence |
| Carlos | 2 VPN deposits + 1 VPN IP | velocity_trends + infrastructure_stability: compound signal |
| Nina | 3 Sao Paulo deposits + VPN IP | infrastructure_stability: impossible travel reinforcement |

### 3. seed_dashboard.py — Evaluation History

**Run:** Called from `seed_data.py` main()

Seeds `Evaluation`, `IndicatorResult`, and `Alert` records for the dashboard demo. Creates historical evaluation data showing how the rule-engine scored each customer over time.

### 4. seed_posture_history.py — Trajectory Snapshots

**Run:** Called from `seed_postures.py`

Creates 6 historical `CustomerRiskPosture` snapshots per customer at `{60d, 30d, 14d, 7d, 3d, 1d}` ago. All snapshots have `is_current=FALSE`.

**Trajectory patterns:**

| Tier | Pattern | Example |
|------|---------|---------|
| Clean | Stable low scores, minor jitter | Sarah: composite 0.04-0.06 across all 6 snapshots |
| Escalate | Linear drift from normal toward watch | David: composite 0.08 → 0.28 over 60 days |
| Fraud | Rapid escalation toward high_risk | Victor: composite 0.15 → 0.65 over 60 days |

**Total:** 96 historical snapshots (16 customers x 6 each).

### 5. seed_postures.py — Compute + Validate

**Run:** `python -m scripts.seed_postures`

Three-step process:

1. **Seed history** — Calls `seed_posture_history()` to insert 96 historical snapshots
2. **Recompute** — Calls `PostureService.recompute_all(trigger="validation")` which runs all 6 signals against live data and persists current postures with `is_current=TRUE`
3. **Validate** — Checks each customer's computed posture against expected tier, prints formatted report with signal breakdowns

**Expected validation output:**

```
  CUST-001  Sarah Chen          [PASS]
  Posture: normal (CLEAN)   Composite: 0.0842
  CUST-007  David Park          [PASS]
  Posture: watch (ESCALATE)   Composite: 0.3821
  CUST-011  Victor Petrov       [PASS]
  Posture: high_risk (FRAUD)   Composite: 0.7234
```

## Design Decisions

### Dynamic NOW

All seed scripts use `datetime.now(timezone.utc)` so that temporal offsets (`_ago(days=7)`) always align with PostgreSQL's `NOW()` used in signal queries. This means:

- Data is always "fresh" relative to the database clock
- No drift between seed timestamps and signal query windows
- Re-running `seed_data.py` produces correctly-windowed data regardless of date

### Deterministic IDs

All customer and entity IDs use `uuid5(NAMESPACE_DNS, "deriv.seed.{name}")`. This means:

- IDs are stable across re-seeds (same customer always gets the same UUID)
- Cross-script references work without passing IDs between scripts
- Enrichments can reference base data entities by name

### Transactional Consistency

- `seed_data.py` runs base data + enrichments + dashboard in a single session with explicit commits after each phase
- `seed_postures.py` uses `PostureService` which manages its own sessions internally (each `save_snapshot()` commits atomically)

## Database State After Full Pipeline

| Table | Records | Source |
|-------|---------|--------|
| customers | 16 | seed_data |
| payment_methods | ~25 | seed_data + enrichments |
| devices | ~22 | seed_data |
| ip_history | ~70 | seed_data + enrichments |
| transactions | ~200+ | seed_data + enrichments |
| trades | ~700+ | seed_data + enrichments |
| withdrawals | ~75+ | seed_data |
| customer_weight_profiles | 16 | seed_data |
| threshold_config | 1 | seed_data |
| evaluations | ~16+ | seed_dashboard |
| customer_risk_postures | 112 | seed_posture_history (96) + recompute_all (16) |

## Signal Data Requirements

Each posture signal queries specific tables. The pipeline ensures every customer has data for all 6:

| Signal | Tables Queried | Time Window |
|--------|---------------|-------------|
| account_maturity | customers, trades | Lifetime + 180d gap analysis |
| velocity_trends | transactions, withdrawals | 7d recent vs 8-30d baseline |
| infrastructure_stability | devices, ip_history | 30d |
| funding_behavior | transactions, trades, withdrawals | Lifetime |
| payment_risk | payment_methods, transactions | Lifetime + 30d failure rate |
| graph_proximity | devices, ip_history, withdrawals, customers.is_flagged | Lifetime (IPs: 30d) |

## Cleanup

To reset all data and start fresh:

```bash
python -m scripts.seed_data       # truncates all tables first
python -m scripts.seed_postures   # recomputes from clean state
```

`seed_data.py` truncates all relevant tables with `CASCADE` before inserting, so re-running is always safe.
