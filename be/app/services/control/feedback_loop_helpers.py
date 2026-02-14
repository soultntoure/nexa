"""DB fetch helpers for the feedback loop service.

Functions:
- fetch_indicator_results_for_evaluation — load 8 indicator rows as dicts
- fetch_decision_history — last N officer decisions with indicator scores
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.evaluation import Evaluation
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.models.withdrawal import Withdrawal
from app.data.db.models.withdrawal_decision import WithdrawalDecision


async def fetch_indicator_results_for_evaluation(
    session: AsyncSession, evaluation_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Load indicator results for an evaluation as plain dicts."""
    stmt = select(IndicatorResult).where(
        IndicatorResult.evaluation_id == evaluation_id
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "indicator_name": r.indicator_name,
            "score": r.score,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "evidence": r.evidence or {},
        }
        for r in rows
    ]


async def fetch_decision_history(
    session: AsyncSession, customer_id: uuid.UUID, limit: int = 20,
) -> list[dict[str, Any]]:
    """Get last N officer decisions with indicator scores and investigator data."""
    rows = await _query_decision_rows(session, customer_id, limit)
    return _group_by_evaluation(rows)


async def _query_decision_rows(
    session: AsyncSession, customer_id: uuid.UUID, limit: int,
) -> list[Any]:
    """Join decisions → evaluations → indicator_results for a customer."""
    stmt = (
        select(
            WithdrawalDecision.decision,
            WithdrawalDecision.decided_at,
            Evaluation.id.label("evaluation_id"),
            Evaluation.decision.label("evaluation_decision"),
            Evaluation.composite_score,
            Evaluation.investigation_data,
            IndicatorResult.indicator_name,
            IndicatorResult.score,
        )
        .join(Evaluation, Evaluation.id == WithdrawalDecision.evaluation_id)
        .join(IndicatorResult, IndicatorResult.evaluation_id == Evaluation.id)
        .join(Withdrawal, Withdrawal.id == WithdrawalDecision.withdrawal_id)
        .where(Withdrawal.customer_id == customer_id)
        .order_by(desc(WithdrawalDecision.decided_at))
        .limit(limit * 8)
    )
    result = await session.execute(stmt)
    return list(result.all())


def _group_by_evaluation(rows: list[Any]) -> list[dict[str, Any]]:
    """Group flat rows into per-evaluation decision dicts."""
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        eval_id = str(row.evaluation_id)
        composite_score = float(row.composite_score) if row.composite_score is not None else 0.0
        evaluation_decision = str(row.evaluation_decision).strip().lower()
        rule_decision = _extract_rule_decision(
            row.investigation_data,
            evaluation_decision,
        )
        if eval_id not in grouped:
            order.append(eval_id)
            grouped[eval_id] = {
                "evaluation_id": eval_id,
                "officer_action": str(row.decision),
                "rule_decision": rule_decision,
                "evaluation_decision": evaluation_decision,
                "composite_score": composite_score,
                "indicator_scores": {},
                "investigator_scores": _extract_investigator_scores(
                    row.investigation_data
                ),
                "decided_at": row.decided_at.isoformat() if row.decided_at else "",
            }
        grouped[eval_id]["indicator_scores"][row.indicator_name] = float(row.score)
    return [grouped[eid] for eid in order]


def _extract_investigator_scores(
    investigation_data: dict | None,
) -> dict[str, float] | None:
    """Pull investigator scores from evaluation's investigation_data JSONB."""
    if not investigation_data:
        return None
    investigators = investigation_data.get("investigators", [])
    if not investigators:
        return None
    scores: dict[str, float] = {}
    for inv in investigators:
        name = inv.get("name")
        score = inv.get("score")
        if name is None or score is None:
            continue
        try:
            scores[str(name)] = float(score)
        except (TypeError, ValueError):
            continue
    return scores or None


def _extract_rule_decision(
    investigation_data: dict | None,
    fallback_decision: str,
) -> str:
    """Get pre-blend rule decision from investigation data when available."""
    if investigation_data:
        rule_engine = investigation_data.get("rule_engine")
        if isinstance(rule_engine, dict):
            decision = rule_engine.get("decision")
            if decision:
                return str(decision).strip().lower()

    return str(fallback_decision).strip().lower()
