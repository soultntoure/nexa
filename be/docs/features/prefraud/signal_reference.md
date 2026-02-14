# Signal Reference -- Pre-Fraud Posture Engine V1

Each signal produces a score from 0.0 (safe) to 1.0 (risky) plus structured evidence and a plain-English reason string. All signals run in parallel with independent database sessions.

---

## Signal Weights and Composite Formula

```python
POSTURE_SIGNAL_WEIGHTS = {
    "account_maturity":          1.0,
    "velocity_trends":           1.2,
    "infrastructure_stability":  1.3,
    "funding_behavior":          1.5,
    "payment_risk":              1.1,
    "graph_proximity":           1.4,
}

POSTURE_GLOBAL_MULTIPLIER = 1.0
```

**Composite calculation:**

```
composite = 1.0 * (am*1.0 + vt*1.2 + is*1.3 + fb*1.5 + pr*1.1 + gp*1.4) / 7.5
```

**Posture mapping:**

| Composite Range | Posture State |
|---|---|
| < 0.30 | `normal` |
| 0.30 -- 0.59 | `watch` |
| >= 0.60 | `high_risk` |

---

## Signal 1: Account Maturity

**File:** `app/services/prefraud/signals/account_maturity.py`

**Purpose:** Flags new, inactive, or recently-reactivated accounts.

**Data sources:** `customers` (registration_date), `trades` (opened_at)

### Sub-signals

| Sub-signal | Weight | Score 0.0 (safe) | Score 1.0 (risky) | Interpolation |
|---|---|---|---|---|
| Account age | 30% | >= 180 days | <= 7 days | Linear between thresholds |
| Total trade count | 25% | >= 50 trades | 0 trades | Linear |
| Activity density (trades/month) | 25% | >= 10/month | < 1/month | Linear |
| Dormancy gap (longest inactive stretch, last 180d) | 20% | 0 days | >= 90 days | Linear |

**Final score:** Weighted average of 4 sub-signals.

**Evidence fields:** `account_age_days`, `total_trades`, `activity_density_per_month`, `dormancy_gap_days`

---

## Signal 2: Velocity Trends

**File:** `app/services/prefraud/signals/velocity_trends.py`

**Purpose:** Detects acceleration in account activity relative to the customer's own baseline.

**Data sources:** `transactions` (type, amount, timestamp), `withdrawals` (submitted_at)

### Methodology

Compares 7-day recent window to 8-30 day baseline window (excluding recent 7 days to avoid self-reference).

### Sub-signals

| Sub-signal | Score 0.0 (safe) | Score 1.0 (risky) | Interpolation |
|---|---|---|---|
| Deposit count ratio (7d / baseline) | ratio <= 1.5 | ratio >= 5.0 | Linear |
| Deposit amount ratio (7d / baseline) | ratio <= 1.5 | ratio >= 5.0 | Linear |
| Withdrawal count ratio (7d / baseline) | ratio <= 1.5 | ratio >= 5.0 | Linear |

**Final score:** Simple average of 3 sub-signals.

**Edge case:** If baseline is zero (no prior activity), any recent activity scores **0.8** (new accounts are inherently velocity-spikey, but not maximally risky).

**Evidence fields:** `deposits_7d_count`, `deposits_7d_amount`, `deposits_baseline_count`, `deposits_baseline_amount`, `withdrawals_7d_count`, `withdrawals_baseline_count`

---

## Signal 3: Infrastructure Stability

**File:** `app/services/prefraud/signals/infrastructure_stability.py`

**Purpose:** Detects device churn, IP instability, and VPN usage patterns.

**Data sources:** `devices` (fingerprint, trusted, first_seen_at), `ip_history` (ip_address, location, is_vpn)

### Sub-signals

| Sub-signal | Weight | Score 0.0 (safe) | Score 1.0 (risky) | Interpolation |
|---|---|---|---|---|
| Device count (30d) | 15% | 1 device | >= 4 devices | Linear |
| Newest device age | 15% | >= 30 days | <= 1 day | Linear |
| Has trusted device | 15% | Yes (0.0) | No (1.0) | Binary |
| Distinct IPs (30d) | 20% | <= 2 IPs | >= 8 IPs | Linear |
| Distinct countries (30d) | 20% | 1 country | >= 4 countries | Linear |
| VPN usage ratio (30d) | 15% | 0% | >= 50% | Linear |

**Final score:** Weighted average of 6 sub-signals.

**Evidence fields:** `device_count_30d`, `newest_device_age_days`, `has_trusted_device`, `distinct_ips_30d`, `distinct_countries_30d`, `vpn_usage_ratio`

---

## Signal 4: Funding Behavior

**File:** `app/services/prefraud/signals/funding_behavior.py`

**Purpose:** Detects deposit-and-run patterns and funding/trading imbalance.

**Data sources:** `transactions` (deposits, withdrawals), `trades` (volume)

### Sub-signals

| Sub-signal | Weight | Score 0.0 (safe) | Score 1.0 (risky) | Notes |
|---|---|---|---|---|
| Deposit-to-trade ratio | 40% | <= 2.0 | >= 20.0 | Deposits with zero trades = 1.0 |
| Deposit-to-withdrawal ratio | 30% | >= 3.0 | <= 1.1 | Low ratio = withdrawing nearly everything |
| Has zero trades (with deposits) | 30% | No | Yes | Binary. No deposits = 0.0 |

**Final score:** Weighted average of 3 sub-signals.

**Edge case:** Zero deposits AND zero trades = score 0.0 (no funding activity to evaluate).

**Evidence fields:** `total_deposits_amount`, `total_withdrawals_amount`, `total_trade_volume`, `deposit_to_trade_ratio`, `deposit_to_withdrawal_ratio`

---

## Signal 5: Payment Risk

**File:** `app/services/prefraud/signals/payment_risk.py`

**Purpose:** Detects method churn, unverified methods, and failed transaction patterns.

**Data sources:** `payment_methods` (type, is_verified, added_at, is_blacklisted), `transactions` (status)

### Sub-signals

| Sub-signal | Weight | Score 0.0 (safe) | Score 1.0 (risky) | Interpolation |
|---|---|---|---|---|
| Method count | 15% | 1-2 methods | >= 5 methods | Linear |
| Average method age | 15% | >= 90 days | <= 7 days | Linear |
| Unverified method ratio | 15% | 0% | >= 50% | Linear |
| Failed transaction rate (30d) | 20% | 0% | >= 30% | Linear |
| Has blacklisted method | 20% | No (0.0) | Yes (1.0) | Binary |
| Newest method age | 15% | >= 30 days | <= 1 day | Linear |

**Final score:** Weighted average of 6 sub-signals.

**Evidence fields:** `method_count`, `avg_method_age_days`, `unverified_ratio`, `failed_tx_rate_30d`, `has_blacklisted`, `newest_method_age_days`

---

## Signal 6: Graph Proximity

**File:** `app/services/prefraud/signals/graph_proximity.py`

**Purpose:** Detects shared infrastructure with other customers. V1 uses direct sharing only (SQL joins, no graph library).

**Data sources:** `devices` (fingerprint), `ip_history` (ip_address), `withdrawals` (recipient_account), `customers` (is_flagged)

### Sub-signals

| Sub-signal | Weight | Score 0.0 (safe) | Score 1.0 (risky) | Interpolation |
|---|---|---|---|---|
| Shared device fingerprint | 35% | 0 other customers | >= 2 other customers | Linear |
| Shared IP address (30d) | 30% | 0 other customers | >= 3 other customers | Linear |
| Shared recipient account | 35% | 0 other customers | >= 1 other customer | Binary (any = 1.0) |

**Flagged connection override:** If any customer sharing an entity has `is_flagged=true`, the signal score is immediately set to **0.9** (overrides sub-signal calculation).

**Second-degree exposure:** Counted and included in evidence but NOT scored in V1. Documents count of customers connected through intermediaries for analyst visibility.

**Scope tag:** Every graph_proximity evidence output includes `"detection_scope": "direct_entity_sharing_only"` to document the V1 limitation.

**Evidence fields:** `shared_device_customers`, `shared_ip_customers`, `shared_recipient_customers`, `flagged_connections`, `second_degree_exposure`, `detection_scope`
