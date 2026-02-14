"""Map review-queue DB rows to QueueResponse schema."""

from __future__ import annotations

from app.api.schemas.fraud.queue import (
    AIRecommendation,
    QueueIndicator,
    QueueInvestigation,
    QueueInvestigatorFinding,
    QueueItem,
    QueueResponse,
    QueueTriage,
    QueueTriageAssignment,
    RiskAssessment,
)
from app.services.fraud.internals.response_builder import INDICATOR_DISPLAY_NAMES


def build_queue_response(rows: list[dict], total: int) -> QueueResponse:
    """Convert enriched DB rows into a paginated QueueResponse."""
    return QueueResponse(
        items=[_build_item(row) for row in rows],
        total=total,
    )


def _build_item(row: dict) -> QueueItem:
    indicators = row.get("indicators", [])
    gray_used = row["gray_zone_used"]

    return QueueItem(
        withdrawal_id=row["withdrawal_id"],
        evaluation_id=row["evaluation_id"],
        customer_id=row["customer_id"],
        customer_name=row["customer_name"],
        customer_email=row["customer_email"],
        amount=float(row["amount"]),
        currency=row["currency"],
        requested_at=row["requested_at"],
        evaluated_at=row["evaluated_at"],
        decision=row["decision"],
        risk_score=row["composite_score"],
        risk_level=row["risk_level"],
        summary=row["summary"],
        risk_assessment=_build_risk_assessment(indicators, gray_used),
        ai_recommendation=_build_ai_recommendation(row),
        investigation=_build_investigation(row.get("investigation_data")),
    )


def _build_risk_assessment(
    indicators: list, gray_used: bool,
) -> RiskAssessment:
    return RiskAssessment(
        type="llm_enhanced" if gray_used else "rule_based",
        indicators=[
            QueueIndicator(
                name=ind.indicator_name,
                display_name=INDICATOR_DISPLAY_NAMES.get(
                    ind.indicator_name, ind.indicator_name,
                ),
                score=ind.score,
                status=_classify_status(ind.score),
                reasoning=ind.reasoning,
            )
            for ind in indicators
        ],
    )


def _build_ai_recommendation(row: dict) -> AIRecommendation:
    if row["gray_zone_used"] and row["gray_zone_reasoning"]:
        return AIRecommendation(
            decision=row["gray_zone_decision"] or row["decision"],
            reasoning=row["gray_zone_reasoning"],
            source="gray_zone_llm",
        )
    source = "investigator" if row.get("investigation_data") else "rule_engine"
    return AIRecommendation(
        decision=row["decision"],
        reasoning=row["summary"],
        source=source,
    )


def _build_investigation(data: dict | None) -> QueueInvestigation | None:
    if not data:
        return None
    triage_data = data["triage"]
    return QueueInvestigation(
        triage=QueueTriage(
            constellation_analysis=triage_data["constellation_analysis"],
            decision=triage_data.get("decision", ""),
            decision_reasoning=triage_data.get("decision_reasoning", ""),
            confidence=triage_data.get("confidence", 0.0),
            risk_score=triage_data.get("risk_score", 0.0),
            assignments=[
                QueueTriageAssignment(**a) for a in triage_data["assignments"]
            ],
            elapsed_s=triage_data["elapsed_s"],
        ),
        investigators=[
            QueueInvestigatorFinding(**inv) for inv in data["investigators"]
        ],
    )


def _classify_status(score: float) -> str:
    if score < 0.3:
        return "pass"
    if score < 0.6:
        return "warn"
    return "fail"
