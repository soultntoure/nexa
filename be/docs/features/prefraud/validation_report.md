# Validation Report -- Pre-Fraud Posture Engine V1

**Date:** 2026-02-12
**Script:** `python -m scripts.seed_postures`
**Database:** 16 seeded customers with posture enrichments
**Elapsed:** 2.19 seconds for full recompute

---

## Summary

| Metric | Value |
|---|---|
| Customers computed | 16 |
| Passed validation | **10 / 16** (62.5%) |
| Failed validation | 6 / 16 |
| Posture distribution | normal: 10, watch: 4, high_risk: 2 |

---

## Full Results

### Clean Customers (expected: `normal`) -- 6/6 PASS

| Customer | Ext ID | Composite | Posture | Status | Top Signal |
|---|---|---|---|---|---|
| Sarah Chen | CUST-001 | 0.0656 | normal | PASS | velocity_trends (0.27) |
| James Wilson | CUST-002 | 0.0721 | normal | PASS | account_maturity (0.18) |
| Aisha Mohammed | CUST-003 | 0.1408 | normal | PASS | velocity_trends (0.33) |
| Kenji Sato | CUST-004 | 0.1163 | normal | PASS | velocity_trends (0.33) |
| Emma Davies | CUST-005 | 0.1584 | normal | PASS | account_maturity (0.35) |
| Raj Patel | CUST-006 | 0.1089 | normal | PASS | velocity_trends (0.33) |

All clean customers score well below the 0.30 threshold. The enrichments successfully establish stable baselines preventing false positives. Scores range from 0.07 to 0.16 -- comfortably in the `normal` band.

### Escalate Customers (expected: `watch`) -- 0/4 PASS

| Customer | Ext ID | Composite | Posture | Status | Gap to 0.30 |
|---|---|---|---|---|---|
| David Park | CUST-007 | 0.2820 | normal | FAIL | -0.018 |
| Maria Santos | CUST-008 | 0.2925 | normal | FAIL | -0.008 |
| Tom Brown | CUST-009 | 0.2060 | normal | FAIL | -0.094 |
| Yuki Tanaka | CUST-010 | 0.1979 | normal | FAIL | -0.102 |

**Signal breakdown for failing escalate customers:**

**David Park** (composite 0.2820, needs +0.018):
- velocity_trends: 0.84 (strong -- deposit spike detected)
- infrastructure_stability: 0.51 (moderate -- multi-country IPs)
- funding_behavior: 0.26 (low)
- graph_proximity: **0.00** (no shared entities)
- payment_risk: **0.00** (no failed txns)

**Maria Santos** (composite 0.2925, needs +0.008):
- velocity_trends: 0.70 (strong)
- payment_risk: 0.55 (moderate -- failed tx + unverified method)
- account_maturity: 0.45 (moderate -- 21-day account)
- graph_proximity: **0.00** (no shared entities)

**Tom Brown** (composite 0.2060, needs +0.094):
- velocity_trends: 0.80 (strong)
- payment_risk: 0.33 (moderate -- 3 failed crypto txns)
- funding_behavior: **0.00** (no deposit/trade imbalance)
- infrastructure_stability: **0.00** (stable infra)

**Yuki Tanaka** (composite 0.1979, needs +0.102):
- velocity_trends: 0.55 (moderate -- post-dormancy spike)
- funding_behavior: 0.30 (low)
- account_maturity: 0.24 (low)
- payment_risk: **0.00** (no payment issues)

### Fraud Customers (expected: `high_risk`) -- 4/6 PASS

| Customer | Ext ID | Composite | Posture | Status | Notes |
|---|---|---|---|---|---|
| Victor Petrov | CUST-011 | 0.5134 | watch | FAIL | Gap to 0.60: -0.087 |
| Sophie Laurent | CUST-012 | 0.6024 | high_risk | PASS | |
| Ahmed Hassan | CUST-013 | 0.5855 | watch | FAIL | Gap to 0.60: -0.015 |
| Fatima Nour | CUST-014 | 0.6800 | high_risk | PASS | |
| Carlos Mendez | CUST-015 | 0.3738 | watch | PASS | Accepts watch or high_risk |
| Nina Volkov | CUST-016 | 0.3055 | watch | PASS | Accepts watch or high_risk |

**Signal breakdown for failing fraud customers:**

**Victor Petrov** (composite 0.5134, needs +0.087):
- account_maturity: 0.72 (strong -- 9-day account)
- velocity_trends: 0.70 (strong)
- funding_behavior: 0.70 (strong -- deposit-and-run)
- graph_proximity: 0.38 (moderate -- shared IP)
- infrastructure_stability: 0.33 (moderate)
- payment_risk: **0.26** (weak -- single verified method)

**Ahmed Hassan** (composite 0.5855, needs +0.015):
- velocity_trends: 0.83 (strong)
- account_maturity: 0.74 (strong)
- graph_proximity: 0.73 (strong -- shared device + IP + recipient)
- funding_behavior: 0.70 (strong)
- infrastructure_stability: 0.25 (moderate)
- payment_risk: **0.24** (weak)

---

## Analysis

### What Works Well

1. **Clean customer separation is excellent.** All 6 clean customers score between 0.07-0.16, well below the 0.30 watch threshold. No false positives.
2. **Fraud ring detection works.** Ahmed, Fatima (shared device + IP + recipient) correctly trigger graph_proximity. Sophie's card testing pattern correctly triggers payment_risk (0.87).
3. **Signal diversity.** Different customer profiles trigger different signal combinations -- the engine is not over-reliant on any single signal.
4. **Velocity detection works.** All escalate and fraud customers with injected deposit spikes show high velocity_trends scores (0.55-1.00).

### Root Cause of Failures

The 6 failures share a common pattern: **zero-scoring signals dilute the composite.**

The composite is a weighted average across all 6 signals. When 2-3 signals score 0.0 (e.g., graph_proximity for customers with no shared entities, payment_risk for customers with no failed transactions), even strong scores on other signals get diluted below thresholds.

**Example:** David Park has velocity_trends=0.84 and infrastructure=0.51, but graph_proximity=0.0, payment_risk=0.0, and account_maturity=0.06. The weighted average: (0.06*1.0 + 0.84*1.2 + 0.51*1.3 + 0.26*1.5 + 0*1.1 + 0*1.4) / 7.5 = **0.282**.

### Remediation Path

The failures are **seed data calibration issues**, not code bugs. Two approaches:

1. **Enrich more signals per customer.** Add shared entities (graph_proximity), failed transactions (payment_risk), or device churn (infrastructure) to customers that currently have 0.0 on those signals.

2. **Increase signal intensity.** Push existing non-zero signals higher (e.g., more deposits for velocity, more IPs for infrastructure) so they compensate for zero-scoring signals.

David Park and Maria Santos are closest to the threshold (need +0.018 and +0.008 respectively) and require minimal tuning. Tom Brown and Yuki Tanaka need more substantial enrichment across multiple signals.

---

## Validation Script

The validation script (`scripts/seed_postures.py`) recomputes postures for all 16 seeded customers and validates each against expected tiers:

```
Clean   (6 customers) -> normal     (composite < 0.30)
Escalate(4 customers) -> watch      (0.30 <= composite < 0.60)
Fraud   (5 customers) -> high_risk  (composite >= 0.60)
```

Carlos (CUST-015) and Nina (CUST-016) accept `watch` OR `high_risk` since their enrichments are profile-dependent.

### Running the Validation

```bash
# From host machine (DB on Docker port 15432):
POSTGRES_URL="postgresql+asyncpg://user:changeme@localhost:15432/fraud_detection" \
  python -m scripts.seed_postures

# From inside Docker container:
python -m scripts.seed_postures
```

### Reseeding Data

```bash
# Reseed all data including enrichments:
POSTGRES_URL="postgresql+asyncpg://user:changeme@localhost:15432/fraud_detection" \
  python -m scripts.seed_data
```
