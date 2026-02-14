"""Service for submitting officer decisions on escalated withdrawals."""

import logging
import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.evaluation import Evaluation
from app.data.db.models.withdrawal_decision import WithdrawalDecision
from app.data.db.repositories.withdrawal_repository import WithdrawalRepository

logger = logging.getLogger(__name__)


async def submit_decision(
    session: AsyncSession,
    withdrawal_id: str,
    evaluation_id: str,
    officer_id: str,
    action: str,
    reason: str,
) -> WithdrawalDecision:
    """Persist an officer's approve/block decision and link to evaluation."""
    repo = WithdrawalRepository(session)

    wid = _uuid.UUID(str(withdrawal_id))
    eid = _uuid.UUID(str(evaluation_id)) if evaluation_id else None

    withdrawal = await repo.get_by_id(wid)
    if not withdrawal:
        raise ValueError(f"Withdrawal {withdrawal_id} not found")
    if withdrawal.decision is not None:
        raise ValueError(f"Decision already exists for withdrawal {withdrawal_id}")

    composite_score = 0.0
    if eid:
        evaluation = await session.get(Evaluation, eid)
        if evaluation and evaluation.composite_score is not None:
            composite_score = float(evaluation.composite_score)
        if not evaluation:
            logger.warning(
                "Decision submitted with missing evaluation: withdrawal=%s evaluation=%s",
                withdrawal_id, evaluation_id,
            )
        elif evaluation.withdrawal_id != wid:
            raise ValueError(
                f"Evaluation {evaluation_id} does not belong to withdrawal {withdrawal_id}"
            )

    now = datetime.now(timezone.utc)
    decision = WithdrawalDecision(
        withdrawal_id=wid,
        evaluation_id=eid,
        decision=action,
        composite_score=composite_score,
        reasoning=f"Officer {officer_id}: {reason}",
        decided_at=now,
    )
    saved = await repo.save_decision(decision)

    logger.info(
        "Decision submitted: withdrawal=%s evaluation=%s action=%s officer=%s",
        withdrawal_id, evaluation_id, action, officer_id,
    )
    return saved
