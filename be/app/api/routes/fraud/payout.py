"""
Payout endpoints — queue, decision, evidence, and stored results.

GET  /api/payout/evaluate/{withdrawal_id} — Get stored indicator results
GET  /api/payout/queue                 — Get review queue for officers
POST /api/payout/decision              — Officer approves/blocks a flagged withdrawal
GET  /api/payout/investigate/{withdrawal_id} — Get investigation evidence
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.fraud.payout import PayoutDecisionRequest, PayoutDecisionResponse
from app.api.schemas.fraud.queue import QueueResponse
from app.data.db.engine import AsyncSessionLocal, get_session
from app.data.db.repositories.queue_repository import QueueRepository
from app.data.db.repositories.indicator_result_repository import IndicatorResultRepository
from app.services.fraud.internals.response_builder import INDICATOR_DISPLAY_NAMES
from app.services.control.evidence_service import get_investigation_evidence
from app.services.control.decision_service import submit_decision
from app.services.control.withdrawal_service import update_withdrawal_status
from app.services.dashboard.queue_mapper import build_queue_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payout", tags=["payout"])


def _fire_feedback_loop(raw_request: Request, body: PayoutDecisionRequest) -> None:
    """Fire feedback loop as a non-blocking background task."""
    try:
        svc = getattr(raw_request.app.state, "feedback_loop_service", None)
        if svc is None:
            logger.warning("FeedbackLoopService not initialized on app.state")
            return
        asyncio.create_task(svc.process_decision(
            withdrawal_id=body.withdrawal_id,
            evaluation_id=body.evaluation_id,
            officer_action=body.action,
        ))
    except Exception as exc:
        logger.warning("Feedback loop failed to start: %s", exc)


@router.get("/evaluate/{withdrawal_id}")
async def get_evaluation(
    withdrawal_id: uuid.UUID,
    evaluation_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get stored indicator results for a withdrawal."""
    repo = IndicatorResultRepository(session)

    if evaluation_id is None:
        evaluation_id = await repo.get_latest_evaluation_id(withdrawal_id)
        if evaluation_id is None:
            raise HTTPException(404, "No evaluation found for this withdrawal.")

    results = await repo.get_by_evaluation_id(evaluation_id)
    if not results:
        raise HTTPException(404, "No evaluation found for this withdrawal.")

    if any(r.withdrawal_id != withdrawal_id for r in results):
        raise HTTPException(404, "Evaluation does not belong to this withdrawal.")

    return {
        "withdrawal_id": str(withdrawal_id),
        "indicators": [
            {
                "name": r.indicator_name,
                "display_name": INDICATOR_DISPLAY_NAMES.get(r.indicator_name, r.indicator_name),
                "score": r.score,
                "weight": r.weight,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "evidence": r.evidence,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ],
    }


@router.get("/queue")
async def get_review_queue(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> QueueResponse:
    """Get pending escalated withdrawals for officer review."""
    try:
        repo = QueueRepository(session)
        rows = await repo.get_review_queue(skip, limit)
        total = await repo.count_review_queue()
        return build_queue_response(rows, total)
    except Exception as exc:
        logger.warning("get_review_queue error: %s", exc)
        return QueueResponse(items=[], total=0)


@router.get("/investigate/{withdrawal_id}")
async def investigate_withdrawal(
    withdrawal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get investigation evidence for a withdrawal's customer."""
    try:
        evidence = await get_investigation_evidence(session, withdrawal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return evidence.model_dump(mode="json")


@router.post("/decision", response_model=PayoutDecisionResponse)
async def submit_payout_decision(
    body: PayoutDecisionRequest,
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
) -> PayoutDecisionResponse:
    """Officer approves or blocks a flagged withdrawal."""
    try:
        decision = await submit_decision(
            session=session,
            withdrawal_id=str(body.withdrawal_id),
            evaluation_id=str(body.evaluation_id) if body.evaluation_id else None,
            officer_id=body.officer_id,
            action=body.action,
            reason=body.reason,
        )
        decided_at = decision.decided_at
    except Exception as exc:
        logger.warning("submit_payout_decision DB error: %s", exc)
        decided_at = datetime.now(timezone.utc)

    try:
        await update_withdrawal_status(
            AsyncSessionLocal, body.withdrawal_id, body.action,
        )
    except Exception as exc:
        logger.warning("Could not update withdrawal status after decision: %s", exc)

    _fire_feedback_loop(raw_request, body)

    return PayoutDecisionResponse(
        withdrawal_id=body.withdrawal_id,
        evaluation_id=body.evaluation_id,
        officer_id=body.officer_id,
        action=body.action,
        reason=body.reason,
        decided_at=decided_at,
    )
