"""
Seed historical posture snapshots for trajectory analysis.

Creates 6 historical snapshots per customer at {60d, 30d, 14d, 7d, 3d, 1d}
before NOW, producing realistic trajectories:

  Clean    (6 customers) - stable "normal" throughout
  Escalate (4 customers) - gradual drift from "normal" -> "watch"
  Fraud    (5 customers) - rapid escalation toward "high_risk"

All snapshots have is_current=FALSE — the real recompute_all() call
in seed_postures.py sets the true current snapshot afterwards.

Run: integrated via seed_postures.py (or standalone for testing)
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.customer_risk_posture import CustomerRiskPosture

# ── Use current time so history snapshots align with DB NOW() ──
NOW = datetime.now(timezone.utc)

SIGNAL_NAMES = [
    "account_maturity",
    "velocity_trends",
    "infrastructure_stability",
    "funding_behavior",
    "payment_risk",
    "graph_proximity",
]

SIGNAL_WEIGHTS = {
    "account_maturity": 1.0,
    "velocity_trends": 1.2,
    "infrastructure_stability": 1.3,
    "funding_behavior": 1.5,
    "payment_risk": 1.1,
    "graph_proximity": 1.4,
}

HISTORY_OFFSETS_DAYS = [60, 30, 14, 7, 3, 1]


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"deriv.seed.{name}")


def _compute_composite(scores: dict[str, float]) -> float:
    total_weighted = sum(scores[s] * SIGNAL_WEIGHTS[s] for s in SIGNAL_NAMES)
    total_weight = sum(SIGNAL_WEIGHTS.values())
    return round(total_weighted / total_weight, 4)


def _map_posture(composite: float) -> str:
    if composite < 0.30:
        return "normal"
    if composite < 0.60:
        return "watch"
    return "high_risk"


def _lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation from start to end at fraction t (0-1)."""
    return round(start + (end - start) * t, 4)


def _build_evidence(scores: dict[str, float]) -> dict:
    """Minimal signal_evidence matching the service's JSONB structure."""
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    top_reasons = [
        f"{name} score {score:.2f}" for name, score in top if score > 0
    ]
    signals = {
        name: {"score": score, "reason": f"Historical snapshot"}
        for name, score in scores.items()
    }
    return {"top_reasons": top_reasons, "signals": signals}


# ═══════════════════════════════════════════════════════════════════════════
# Trajectory definitions per customer
#
# Each entry: (seed_name, final_scores)
# The function interpolates from a starting profile to these final scores
# across the 6 history offsets.
# ═══════════════════════════════════════════════════════════════════════════

# Clean customers: stable low scores throughout.
# start ≈ final (minor fluctuation only)
CLEAN_CUSTOMERS = [
    ("sarah", {
        "account_maturity": 0.05, "velocity_trends": 0.08,
        "infrastructure_stability": 0.04, "funding_behavior": 0.06,
        "payment_risk": 0.03, "graph_proximity": 0.02,
    }),
    ("james", {
        "account_maturity": 0.03, "velocity_trends": 0.10,
        "infrastructure_stability": 0.05, "funding_behavior": 0.07,
        "payment_risk": 0.04, "graph_proximity": 0.02,
    }),
    ("aisha", {
        "account_maturity": 0.10, "velocity_trends": 0.09,
        "infrastructure_stability": 0.06, "funding_behavior": 0.08,
        "payment_risk": 0.05, "graph_proximity": 0.02,
    }),
    ("kenji", {
        "account_maturity": 0.07, "velocity_trends": 0.08,
        "infrastructure_stability": 0.05, "funding_behavior": 0.07,
        "payment_risk": 0.06, "graph_proximity": 0.03,
    }),
    ("emma", {
        "account_maturity": 0.04, "velocity_trends": 0.12,
        "infrastructure_stability": 0.03, "funding_behavior": 0.09,
        "payment_risk": 0.04, "graph_proximity": 0.02,
    }),
    ("raj", {
        "account_maturity": 0.06, "velocity_trends": 0.10,
        "infrastructure_stability": 0.05, "funding_behavior": 0.08,
        "payment_risk": 0.04, "graph_proximity": 0.03,
    }),
]

# Escalate customers: drift from normal toward watch.
# start_scores -> final_scores across timeline
ESCALATE_CUSTOMERS = [
    ("david", {
        "start": {
            "account_maturity": 0.10, "velocity_trends": 0.08,
            "infrastructure_stability": 0.12, "funding_behavior": 0.06,
            "payment_risk": 0.05, "graph_proximity": 0.03,
        },
        "end": {
            "account_maturity": 0.12, "velocity_trends": 0.35,
            "infrastructure_stability": 0.52, "funding_behavior": 0.15,
            "payment_risk": 0.08, "graph_proximity": 0.10,
        },
    }),
    ("maria", {
        "start": {
            "account_maturity": 0.30, "velocity_trends": 0.10,
            "infrastructure_stability": 0.05, "funding_behavior": 0.12,
            "payment_risk": 0.08, "graph_proximity": 0.02,
        },
        "end": {
            "account_maturity": 0.35, "velocity_trends": 0.45,
            "infrastructure_stability": 0.08, "funding_behavior": 0.40,
            "payment_risk": 0.22, "graph_proximity": 0.04,
        },
    }),
    ("tom", {
        "start": {
            "account_maturity": 0.06, "velocity_trends": 0.07,
            "infrastructure_stability": 0.05, "funding_behavior": 0.08,
            "payment_risk": 0.04, "graph_proximity": 0.03,
        },
        "end": {
            "account_maturity": 0.08, "velocity_trends": 0.25,
            "infrastructure_stability": 0.06, "funding_behavior": 0.18,
            "payment_risk": 0.55, "graph_proximity": 0.05,
        },
    }),
    ("yuki", {
        "start": {
            "account_maturity": 0.05, "velocity_trends": 0.06,
            "infrastructure_stability": 0.04, "funding_behavior": 0.05,
            "payment_risk": 0.03, "graph_proximity": 0.02,
        },
        "end": {
            "account_maturity": 0.40, "velocity_trends": 0.38,
            "infrastructure_stability": 0.10, "funding_behavior": 0.32,
            "payment_risk": 0.06, "graph_proximity": 0.04,
        },
    }),
]

# Fraud customers: rapid escalation toward high_risk.
FRAUD_CUSTOMERS = [
    ("victor", {
        "start": {
            "account_maturity": 0.45, "velocity_trends": 0.10,
            "infrastructure_stability": 0.08, "funding_behavior": 0.15,
            "payment_risk": 0.06, "graph_proximity": 0.05,
        },
        "end": {
            "account_maturity": 0.55, "velocity_trends": 0.82,
            "infrastructure_stability": 0.20, "funding_behavior": 0.90,
            "payment_risk": 0.12, "graph_proximity": 0.65,
        },
    }),
    ("sophie", {
        "start": {
            "account_maturity": 0.35, "velocity_trends": 0.08,
            "infrastructure_stability": 0.10, "funding_behavior": 0.12,
            "payment_risk": 0.30, "graph_proximity": 0.15,
        },
        "end": {
            "account_maturity": 0.40, "velocity_trends": 0.30,
            "infrastructure_stability": 0.25, "funding_behavior": 0.70,
            "payment_risk": 0.78, "graph_proximity": 0.55,
        },
    }),
    ("ahmed", {
        "start": {
            "account_maturity": 0.42, "velocity_trends": 0.12,
            "infrastructure_stability": 0.10, "funding_behavior": 0.18,
            "payment_risk": 0.06, "graph_proximity": 0.20,
        },
        "end": {
            "account_maturity": 0.48, "velocity_trends": 0.75,
            "infrastructure_stability": 0.15, "funding_behavior": 0.85,
            "payment_risk": 0.10, "graph_proximity": 0.80,
        },
    }),
    ("fatima", {
        "start": {
            "account_maturity": 0.42, "velocity_trends": 0.10,
            "infrastructure_stability": 0.10, "funding_behavior": 0.20,
            "payment_risk": 0.05, "graph_proximity": 0.22,
        },
        "end": {
            "account_maturity": 0.48, "velocity_trends": 0.70,
            "infrastructure_stability": 0.15, "funding_behavior": 0.92,
            "payment_risk": 0.08, "graph_proximity": 0.82,
        },
    }),
    ("carlos", {
        "start": {
            "account_maturity": 0.18, "velocity_trends": 0.15,
            "infrastructure_stability": 0.20, "funding_behavior": 0.10,
            "payment_risk": 0.08, "graph_proximity": 0.05,
        },
        "end": {
            "account_maturity": 0.22, "velocity_trends": 0.85,
            "infrastructure_stability": 0.55, "funding_behavior": 0.35,
            "payment_risk": 0.12, "graph_proximity": 0.10,
        },
    }),
    ("nina", {
        "start": {
            "account_maturity": 0.20, "velocity_trends": 0.06,
            "infrastructure_stability": 0.08, "funding_behavior": 0.10,
            "payment_risk": 0.05, "graph_proximity": 0.03,
        },
        "end": {
            "account_maturity": 0.25, "velocity_trends": 0.45,
            "infrastructure_stability": 0.80, "funding_behavior": 0.40,
            "payment_risk": 0.10, "graph_proximity": 0.08,
        },
    }),
]


def _build_clean_snapshots(
    name: str,
    final_scores: dict[str, float],
) -> list[CustomerRiskPosture]:
    """Generate stable snapshots for a clean customer (minor jitter only)."""
    cid = _id(name)
    snapshots = []

    for i, offset_days in enumerate(HISTORY_OFFSETS_DAYS):
        # Small random-looking jitter based on index (deterministic)
        jitter = (i % 3 - 1) * 0.02
        scores = {
            sig: max(0.0, min(1.0, round(val + jitter, 4)))
            for sig, val in final_scores.items()
        }
        composite = _compute_composite(scores)
        computed_at = NOW - timedelta(days=offset_days)

        snapshots.append(CustomerRiskPosture(
            id=uuid.uuid4(),
            customer_id=cid,
            posture=_map_posture(composite),
            composite_score=composite,
            signal_scores=scores,
            signal_evidence=_build_evidence(scores),
            trigger="scheduled",
            is_current=False,
            computed_at=computed_at,
            created_at=computed_at,
        ))

    return snapshots


def _build_drift_snapshots(
    name: str,
    trajectory: dict[str, dict[str, float]],
) -> list[CustomerRiskPosture]:
    """Generate interpolated snapshots from start -> end scores."""
    cid = _id(name)
    start = trajectory["start"]
    end = trajectory["end"]
    n = len(HISTORY_OFFSETS_DAYS)
    snapshots = []

    for i, offset_days in enumerate(HISTORY_OFFSETS_DAYS):
        t = i / max(n - 1, 1)
        scores = {
            sig: _lerp(start[sig], end[sig], t)
            for sig in SIGNAL_NAMES
        }
        composite = _compute_composite(scores)
        computed_at = NOW - timedelta(days=offset_days)

        snapshots.append(CustomerRiskPosture(
            id=uuid.uuid4(),
            customer_id=cid,
            posture=_map_posture(composite),
            composite_score=composite,
            signal_scores=scores,
            signal_evidence=_build_evidence(scores),
            trigger="scheduled",
            is_current=False,
            computed_at=computed_at,
            created_at=computed_at,
        ))

    return snapshots


async def seed_posture_history(session: AsyncSession) -> int:
    """Seed historical posture snapshots for all 16 customers.

    Returns:
        Number of snapshots created.
    """
    all_snapshots: list[CustomerRiskPosture] = []

    for name, final_scores in CLEAN_CUSTOMERS:
        all_snapshots.extend(_build_clean_snapshots(name, final_scores))

    for name, trajectory in ESCALATE_CUSTOMERS:
        all_snapshots.extend(_build_drift_snapshots(name, trajectory))

    for name, trajectory in FRAUD_CUSTOMERS:
        all_snapshots.extend(_build_drift_snapshots(name, trajectory))

    session.add_all(all_snapshots)
    return len(all_snapshots)
