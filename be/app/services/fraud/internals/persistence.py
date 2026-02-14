"""ORM model builders and persistence for fraud evaluation results."""

import logging
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agentic_system.schemas.indicators import IndicatorResult
from app.api.schemas.fraud.fraud_check import FraudCheckRequest
from app.core.scoring import APPROVE_THRESHOLD, BLOCK_THRESHOLD, INDICATOR_WEIGHTS, ScoringResult

logger = logging.getLogger(__name__)


def build_indicator_models(
    evaluation_id: uuid.UUID,
    withdrawal_id: uuid.UUID,
    results: list[IndicatorResult],
) -> list:
    """Create IndicatorResult ORM models from raw results."""
    from app.data.db.models.indicator_result import (
        IndicatorResult as IndicatorResultModel,
    )

    return [
        IndicatorResultModel(
            withdrawal_id=withdrawal_id,
            evaluation_id=evaluation_id,
            indicator_name=r.indicator_name,
            score=r.score,
            weight=INDICATOR_WEIGHTS.get(r.indicator_name, 1.0),
            confidence=r.confidence,
            reasoning=r.reasoning,
            evidence=r.evidence,
        )
        for r in results
    ]


async def persist_investigation(
    session_factory: async_sessionmaker,
    evaluation_id: uuid.UUID,
    request: FraudCheckRequest,
    results: list[IndicatorResult],
    scoring: ScoringResult,
    decision: str,
    risk_score: float,
    elapsed: float,
    investigation_data: dict | None = None,
    approve_threshold: float = APPROVE_THRESHOLD,
    block_threshold: float = BLOCK_THRESHOLD,
) -> None:
    """Persist evaluation + indicator results to DB."""
    from app.data.db.models.evaluation import Evaluation
    from app.data.db.repositories.withdrawal_repository import WithdrawalRepository

    risk_level = (
        "high" if risk_score >= block_threshold
        else "medium" if risk_score >= approve_threshold
        else "low"
    )

    try:
        evaluation = Evaluation(
            id=evaluation_id,
            withdrawal_id=request.withdrawal_id,
            composite_score=risk_score,
            decision=decision,
            risk_level=risk_level,
            summary=scoring.reasoning,
            has_hard_escalation=False,
            has_multi_critical=False,
            gray_zone_used=False,
            investigation_data=investigation_data,
            elapsed_s=elapsed,
        )
        async with session_factory() as session:
            repo = WithdrawalRepository(session)
            await repo.save_evaluation(evaluation)

        db_indicators = build_indicator_models(
            evaluation_id, request.withdrawal_id, results,
        )
        if db_indicators:
            async with session_factory() as session:
                repo = WithdrawalRepository(session)
                await repo.save_indicator_results(db_indicators)

        logger.info(
            "Investigation persisted: eval=%s indicators=%d",
            evaluation_id, len(db_indicators),
        )
    except Exception:
        logger.exception("Failed to persist investigation %s", evaluation_id)
