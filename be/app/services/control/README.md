# Control Service

**Role**: Officer actions, feedback learning, and investigation evidence gathering. Implements human-in-the-loop decision lifecycle and fraud pattern calibration.

## Overview

This service layer handles all operations triggered by fraud officers:
1. **Officer Decisions** — approve/block evaluations, removed from queue
2. **Fraud Patterns** — alert management, bulk account lockdowns, fraud ring detection
3. **Learning Loop** — records decision patterns, recalibrates per-customer weights
4. **Evidence Gathering** — customer history (withdrawals, IPs, devices) for investigation
5. **Configuration** — threshold and weight management

**Key principle**: Fire-and-forget feedback loops (async, non-blocking) + repository pattern for all DB access.

## File Summary

| File | Lines | Role | Public Functions |
|------|-------|------|------------------|
| `decision_service.py` | 67 | Officer decision persistence | `submit_decision()` |
| `alert_service.py` | 260 | Alert listing + bulk actions | `list_alerts()`, `execute_bulk_action()`, `create_fraud_alert()` |
| `evidence_service.py` | 129 | Investigation evidence gathering | `get_investigation_evidence()` |
| `withdrawal_service.py` | 78 | Withdrawal lifecycle | `ensure_withdrawal_exists()`, `update_withdrawal_status()` |
| `card_lockdown_service.py` | 266 | Fraud ring detection | `execute_card_lockdown_by_customer()`, `check_shared_card()` |
| `customer_weight_explain_service.py` | 179 | Personalization & audit | `get_snapshot()`, `get_history()`, `reset_to_baseline()` |
| `feedback_loop_service.py` | 139 | Decision learning orchestrator | `FeedbackLoopService.process_decision()` |
| `feedback_loop_helpers.py` | 142 | DB fetch helpers | `fetch_decision_history()`, `fetch_indicator_results_for_evaluation()` |
| `threshold_service.py` | 44 | Config CRUD | `get_active_thresholds()`, `save_thresholds()` |
| `__init__.py` | 1 | Module marker | (none) |

## Officer Decision Flow

**Trigger**: `POST /api/payout/{id}/submit-decision` with officer action (approve/block) + notes

**Sequence**:
```
request → decision_service.submit_decision()
  ├─ Validate withdrawal exists
  ├─ Validate no prior decision
  ├─ Create WithdrawalDecision record (evaluation_id, officer_id, reasoning)
  ├─ Update withdrawal.status → approved/blocked
  ├─ Log decision
  └─ Return WithdrawalDecision

→ (async, fire-and-forget via asyncio.create_task)
  FeedbackLoopService.process_decision()
    ├─ Loop 1: Record Pattern
    │   ├─ fetch_indicator_results_for_evaluation() → [8 indicators]
    │   ├─ extract_fingerprint() → unique indicator combo + signal type
    │   └─ CustomerFraudSignalRepository.upsert_pattern()
    └─ Loop 2: Recalibrate Weights
        ├─ fetch_decision_history() → last 20 officer decisions
        ├─ recalculate_profile() → new indicator multipliers
        ├─ calculate_blend_weights() → rule/investigator split
        └─ WeightProfileRepository.save_profile()
```

**Non-blocking**: Officer sees immediate response; feedback loop completes in background.

## Alert & Pattern Management

### Alert Listing

**Source** (`alert_service.py:47-67`):
- Fetches recent 50 alerts (joined with customer + withdrawal)
- For each alert, queries top 3 indicators from evaluation
- Computes 4 fraud patterns (see below)
- Returns: alerts[], total count, patterns[]

### Fraud Pattern Stats

**Definitions** (`alert_service.py:134-150`):
Four hardcoded patterns with threshold + confidence:

| Pattern | Indicator | Threshold | Confidence | Detects |
|---------|-----------|-----------|------------|---------|
| No Trade Pattern | trading_behavior | 0.70 | 94% | Account never traded before withdrawal |
| Velocity Abuse | velocity | 0.60 | 78% | Multiple transactions in short time |
| Card Testing | card_errors | 0.50 | 91% | Repeated failed card attempts |
| Geographic Anomaly | geographic | 0.60 | 87% | Impossible travel distance |

**Calculation** (`alert_service.py:152-173`):
- Groups indicator results by withdrawal
- Counts distinct withdrawals above threshold
- Sums withdrawal amounts (total exposure)
- Returns per-pattern: accounts_affected, total_exposure, confidence

### Bulk Actions

**Source** (`alert_service.py:176-195`):
Three actions supported:

1. **Dismiss** — Mark alerts as read (admin acknowledgment)
2. **Lock Accounts** — Flag customers, block pending/escalated withdrawals
3. **Freeze Withdrawals** — Update withdrawal status to blocked

**Rollback**: On error, `session.rollback()` discards all changes.

## Fraud Ring Detection (Card Lockdown)

**Trigger**: Auto-called when evaluation decision = blocked + card payment method

**Source** (`card_lockdown_service.py:22-72`):

**Flow**:
```
check_shared_card(customer_id)
  ├─ Resolve customer by external_id
  ├─ Get latest card payment method
  └─ Find other customers using same card
      → PaymentMethodRepository.find_linked_by_card()
      → Return linked_accounts[]

execute_card_lockdown_by_customer(customer_id, risk_score)
  ├─ Get customer + latest card + latest withdrawal
  └─ _execute_lockdown()
      ├─ Find all payment methods linked to card
      ├─ Flag all affected customers
      ├─ Blacklist all linked payment methods
      ├─ Create card_lockdown alerts (one per affected customer)
      └─ Return affected_accounts[], blacklisted_count
```

**Example**: If CUST-001 and CUST-005 both use card ending in 4242, blocking CUST-001 flags CUST-005 and blacklists the card globally.

**Alert Deduplication** (`card_lockdown_service.py:200-218`):
- Skips creating duplicate "card_lockdown" alerts for same customer
- Allows one per customer across all lockdown events

## Customer Weight Personalization

### Snapshot (Current State)

**Source** (`customer_weight_explain_service.py:29-35`):

**Returns** (`WeightSnapshotResponse`):
- **Personalization status**: "applied" | "limited data" | "baseline fallback"
- **Blend weights**: baseline (60/40 rule/investigator) vs customer-specific
- **Indicator weights**: 8 rows with baseline, customer multiplier, difference, status
- **Sample count**: How many decisions in feedback window

**Example**:
```json
{
  "customer_id": "CUST-001",
  "personalization_status": "applied",
  "sample_count": 12,
  "blend": {
    "baseline": {"rule_engine": 0.60, "investigators": 0.40},
    "customer": {"rule_engine": 0.55, "investigators": 0.45}
  },
  "indicators": [
    {
      "name": "velocity",
      "baseline_weight": 0.15,
      "customer_multiplier": 1.2,
      "customer_weight": 0.18,
      "difference": 0.03,
      "status": "stable"
    }
  ]
}
```

### Weight Calibration Logic

**Trigger**: Officer submits decision → feedback_loop_service fires

**Source** (`feedback_loop_service.py:85-102`):
```python
recalibrate_weights(customer_id):
  ├─ fetch_decision_history(customer_id) → last 20 officer decisions
  ├─ recalculate_profile(decisions, current_weights) → new multipliers
  │   (from app/core/calibration)
  │   Algorithm: compares officer decisions vs evaluation predictions
  │              adjusts multipliers for indicators that mis-predicted
  ├─ calculate_blend_weights(decisions) → new rule/investigator blend
  └─ Save as CustomerWeightProfile(active=true, previous=inactive)
```

**Status Levels**:
- **"stable"** — min 5 decisions, multiplier locked
- **"limited data"** — < 5 decisions, multiplier provisional
- **"baseline fallback"** — no profile or no data, use defaults

### Audit Trail

**Source** (`customer_weight_explain_service.py:38-59`):
- `get_history()` returns last 20 weight profile snapshots
- Each includes: timestamp, indicator_weights, blend_weights, is_active flag
- Officers can review how personalization evolved

## Evidence Service

**Purpose**: Fetch customer context for queue item investigation

**Source** (`evidence_service.py:21-37`):

**Returns** (`InvestigateResponse`):
1. **Customer Summary** — name, country, registration date, is_flagged
2. **Recent Withdrawals** — last 5, with amount/status/recipient
3. **IP History** — last 10 IPs, location, VPN status, last seen
4. **Device History** — last 10 devices, OS, browser, fingerprint, trusted flag

**Usage**: Officers click queue item → sidebar shows customer profile + past activity → inform decision.

## Withdrawal Lifecycle

**Create** (`withdrawal_service.py:17-63`):
- `ensure_withdrawal_exists()` — idempotent, creates if not present
- Validates customer exists, has payment method
- Stores metadata: ip_address, device_fingerprint, recipient_name

**Update** (`withdrawal_service.py:66-77`):
- `update_withdrawal_status()` — changes status after evaluation/decision
- Sets processed_at timestamp

**Usage**: Called from payout API routes when evaluation completes.

## Architecture Diagram

```mermaid
graph TB
    subgraph API
        D1["POST /api/payout/{id}/submit-decision"]
        D2["GET /api/alerts"]
        D3["POST /api/payout/bulk-action"]
    end

    subgraph Control Services
        DS["decision_service<br/>(persist decision)"]
        AS["alert_service<br/>(list + bulk)"]
        ES["evidence_service<br/>(gather context)"]
        WS["withdrawal_service<br/>(lifecycle)"]
        CLS["card_lockdown_service<br/>(fraud ring)"]
        CWES["customer_weight_explain<br/>(personalization audit)"]
        FLS["feedback_loop_service<br/>(async learning)"]
    end

    subgraph Core Logic
        FLH["feedback_loop_helpers<br/>(DB fetch)"]
        CAL["core/calibration<br/>(recalc weights)"]
        PFP["core/pattern_fingerprint<br/>(extract pattern)"]
    end

    subgraph Data Repositories
        WR["WithdrawalRepository"]
        PR["PaymentMethodRepository"]
        WPR["WeightProfileRepository"]
        CFSR["CustomerFraudSignalRepository"]
    end

    D1 --> DS
    DS --> |async| FLS
    FLS --> FLH
    FLS --> CAL
    FLS --> PFP
    FLS --> CFSR
    FLS --> WPR

    D2 --> AS
    D3 --> AS
    D3 --> CLS
    CLS --> PR

    ES --> |fetch evidence| WR
    WS --> WR

    CWES --> |query profiles| WPR

    style DS fill:#4A90E2,stroke:#333,stroke-width:2px
    style FLS fill:#BD10E0,stroke:#333,stroke-width:2px
    style AS fill:#F5A623,stroke:#333,stroke-width:2px
EOF
