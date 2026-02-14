"""Seed evaluations for original fraud customers (CUST-011 to CUST-016).

These are needed so AuditTextUnit FK references to evaluations.id are valid.
Lightweight: just enough for the audit pipeline to have real FKs.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import Evaluation, IndicatorResult, WithdrawalDecision

from .constants import NOW, _id

# (customer_key, wd_key, score, decision, risk, summary)
_ORIG_EVALS: list[tuple[str, str, float, str, str, str]] = [
    ("victor", "victor.wd.pending", 0.85, "blocked", "high",
     "No-trade fraud: $2990 withdrawal, 1 token trade, 5-day account."),
    ("sophie", "sophie.wd.pending", 0.78, "blocked", "high",
     "Card testing: 3 failed cards, minimal trading, shared device."),
    ("ahmed", "ahmed.wd.pending", 0.82, "blocked", "high",
     "Fraud ring: shared device/IP/recipient with CUST-014."),
    ("fatima", "fatima.wd.pending", 0.84, "blocked", "high",
     "Fraud ring: zero trades, shared device/IP/recipient with CUST-013."),
    ("carlos", "carlos.wd.0", 0.75, "blocked", "high",
     "Velocity abuse: 5 withdrawals in 1 hour from 3 devices via VPN."),
    ("nina", "nina.wd.pending", 0.80, "blocked", "high",
     "Impossible travel + rapid funding cycles + new device."),
]

# Minimal indicator set for each — 8 indicators with representative scores
_BASE_INDICATORS: list[tuple[str, float, float, float, str]] = [
    ("velocity", 0.50, 1.0, 0.85, "Moderate velocity signal."),
    ("amount_anomaly", 0.60, 1.0, 0.82, "Withdrawal amount anomaly detected."),
    ("no_trade", 0.70, 1.0, 0.88, "Minimal or no trading activity."),
    ("card_errors", 0.20, 1.5, 0.90, "Low card error signal."),
    ("geographic", 0.30, 1.0, 0.85, "Geographic signal present."),
    ("rapid_funding", 0.40, 1.0, 0.80, "Moderate rapid funding signal."),
    ("device_fingerprint", 0.65, 1.5, 0.90, "Device sharing detected."),
    ("recipient", 0.35, 1.0, 0.85, "Recipient analysis signal."),
]


async def _seed_evaluations_orig(s: AsyncSession) -> None:
    """Create evaluations + indicator results + decisions for CUST-011–016."""
    for cust_key, wd_key, score, decision, risk, summary in _ORIG_EVALS:
        wd_id = _id(wd_key)
        eval_id = _id(f"{cust_key}.eval")

        s.add(Evaluation(
            id=eval_id,
            withdrawal_id=wd_id,
            composite_score=score,
            decision=decision,
            risk_level=risk,
            summary=summary,
            investigation_data={"triage": {"constellation_analysis": summary},
                                "investigators": []},
            has_hard_escalation=True,
            has_multi_critical=score >= 0.70,
            gray_zone_used=False,
            elapsed_s=0.3,
            checked_at=NOW,
        ))

        for name, ind_score, weight, conf, reasoning in _BASE_INDICATORS:
            s.add(IndicatorResult(
                id=uuid.uuid4(),
                withdrawal_id=wd_id,
                evaluation_id=eval_id,
                indicator_name=name,
                score=ind_score,
                weight=weight,
                confidence=conf,
                reasoning=reasoning,
                evidence={"source": "seed", "score": ind_score},
                created_at=NOW,
            ))

        s.add(WithdrawalDecision(
            id=uuid.uuid4(),
            withdrawal_id=wd_id,
            evaluation_id=eval_id,
            decision=decision,
            composite_score=score,
            reasoning=summary,
            decided_at=NOW,
            created_at=NOW,
        ))
