"""Investigator endpoint returning structured investigator payloads."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.api.schemas.fraud.fraud_check import FraudCheckRequest
from app.api.schemas.fraud.investigator import (
    InvestigatorAssignmentDetail,
    InvestigatorFinding,
    InvestigatorResponse,
    TriageDetail,
)
from app.core.scoring import ScoringResult
from app.services.fraud.internals.response_builder import (
    INDICATOR_DISPLAY_NAMES,
    build_response,
)
from app.data.db.engine import AsyncSessionLocal
from app.services.control.withdrawal_service import (
    ensure_withdrawal_exists,
    update_withdrawal_status,
)
from app.data.db.models.customer import Customer
from app.services.control.alert_service import create_fraud_alert
from app.services.fraud.investigator_service import InvestigatorService
from app.services.prefraud.posture_scheduler import trigger_recompute

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])


def _get_service(request: Request) -> InvestigatorService:
    svc = getattr(request.app.state, "investigator_service", None)
    if svc is None:
        from app.config import get_settings
        from app.data.db.engine import AsyncSessionLocal

        settings = get_settings()
        sync_uri = settings.POSTGRES_URL.replace("+asyncpg", "").split("?")[0]
        svc = InvestigatorService(AsyncSessionLocal, sync_uri)
        request.app.state.investigator_service = svc
    return svc


def _align_score_with_decision(
    score: float,
    decision: str,
    approve_threshold: float = 0.30,
    block_threshold: float = 0.70,
) -> float:
    if decision == "blocked":
        return max(score, block_threshold)
    if decision == "escalated":
        return max(score, approve_threshold)
    return score


def _build_triage_detail(raw: dict) -> TriageDetail:
    """Extract triage verdict detail from raw pipeline output."""
    triage = raw["triage"]
    return TriageDetail(
        constellation_analysis=triage.constellation_analysis,
        decision=triage.decision,
        decision_reasoning=triage.decision_reasoning,
        confidence=triage.confidence,
        risk_score=triage.risk_score,
        assignments=[
            InvestigatorAssignmentDetail(
                investigator=a.investigator,
                priority=a.priority,
            )
            for a in triage.assignments
        ],
        elapsed_s=raw["triage_elapsed_s"],
    )


def _build_investigator_findings(raw: dict) -> list[InvestigatorFinding]:
    """Extract investigator findings from raw pipeline output."""
    findings = []
    for f in raw["findings"]:
        result = f.get("result")
        if result is None:
            continue
        findings.append(InvestigatorFinding(
            investigator_name=result.investigator_name,
            display_name=INDICATOR_DISPLAY_NAMES.get(
                result.investigator_name, result.investigator_name,
            ),
            score=result.score,
            confidence=result.confidence,
            reasoning=result.reasoning,
            evidence=result.evidence,
            elapsed_s=f["elapsed_s"],
        ))
    return findings


@router.post("/investigate", response_model=InvestigatorResponse)
async def investigate_payout(
    request: FraudCheckRequest,
    raw_request: Request,
    service: InvestigatorService = Depends(_get_service),
) -> InvestigatorResponse:
    """Create withdrawal record, run investigators, return structured response."""
    await ensure_withdrawal_exists(
        session_factory=AsyncSessionLocal,
        withdrawal_id=request.withdrawal_id,
        customer_id=request.customer_id,
        amount=request.amount,
        recipient_name=request.recipient_name,
        recipient_account=request.recipient_account,
        ip_address=request.ip_address,
        device_fingerprint=request.device_fingerprint,
    )

    # Fire-and-forget posture recompute on withdrawal event
    posture_svc = getattr(raw_request.app.state, "posture_service", None)
    if posture_svc:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Customer.id).where(
                    Customer.external_id == request.customer_id,
                )
            )
            customer_uuid = result.scalar_one_or_none()
        if customer_uuid:
            trigger_recompute(posture_svc, customer_uuid, "event:withdrawal_request")

    raw = await service.investigate(request)

    decision = raw["decision"]
    await update_withdrawal_status(
        AsyncSessionLocal, request.withdrawal_id, decision,
    )

    if decision in ("blocked", "escalated"):
        top_indicators = [
            r.indicator_name
            for r in sorted(raw["results"], key=lambda r: r.score, reverse=True)[:3]
        ]
        await create_fraud_alert(
            session_factory=AsyncSessionLocal,
            customer_id=request.customer_id,
            withdrawal_id=request.withdrawal_id,
            risk_score=raw["risk_score"],
            decision=decision,
            indicator_names=top_indicators,
        )
    aligned_score = round(_align_score_with_decision(
        raw["risk_score"], decision,
        approve_threshold=raw.get("approve_threshold", 0.30),
        block_threshold=raw.get("block_threshold", 0.70),
    ), 4)
    rule_scoring = raw["scoring"]
    scoring = ScoringResult(
        decision=decision,
        composite_score=aligned_score,
        weighted_breakdown=rule_scoring.weighted_breakdown,
        reasoning=rule_scoring.reasoning,
    )

    base = build_response(
        evaluation_id=raw["evaluation_id"],
        decision=decision,
        scoring=scoring,
        results=raw["results"],
        elapsed=raw["total_elapsed_s"],
    )

    return InvestigatorResponse(
        evaluation_id=base.evaluation_id,
        decision=base.decision,
        risk_score=base.risk_score,
        risk_percent=base.risk_percent,
        risk_level=base.risk_level,
        summary=base.summary,
        indicators=base.indicators,
        scoring=base.scoring,
        triage=_build_triage_detail(raw),
        investigators=_build_investigator_findings(raw),
        rule_engine_elapsed_s=raw["rule_engine_elapsed_s"],
        total_elapsed_s=raw["total_elapsed_s"],
        elapsed_s=base.elapsed_s,
        checked_at=base.checked_at,
    )
