"""Build the FraudCheckResponse from scored indicator results."""

import uuid
from datetime import datetime, timezone

from app.agentic_system.schemas.indicators import IndicatorResult
from app.api.schemas.fraud.fraud_check import (
    FraudCheckResponse,
    IndicatorDetail,
    ScoringDetail,
)
from app.core.scoring import INDICATOR_WEIGHTS, ScoringResult

INDICATOR_DISPLAY_NAMES: dict[str, str] = {
    "recipient": "Identity Verified",
    "geographic": "VPN Detection",
    "trading_behavior": "Trading History",
    "velocity": "Account Age",
    "amount_anomaly": "Withdrawal Pattern",
    "device_fingerprint": "Device Recognition",
    "payment_method": "Payment Method",
    "card_errors": "Transaction Errors",
    "financial_behavior": "Financial Behavior Analyst",
    "identity_access": "Identity & Access Analyst",
    "cross_account": "Cross-Account Investigator",
}

_STATUS_PRIORITY = {"fail": 0, "warn": 1, "pass": 2}


def build_response(
    evaluation_id: uuid.UUID,
    decision: str,
    scoring: ScoringResult,
    results: list[IndicatorResult],
    elapsed: float,
) -> FraudCheckResponse:
    """Assemble the full fraud-check response."""
    indicators = _build_indicator_details(results)
    has_hard = any(r.score >= 0.7 and r.confidence >= 0.8 for r in results)
    has_multi = (
        sum(1 for r in results if r.score >= 0.6 and r.confidence >= 0.8) >= 2
    )

    return FraudCheckResponse(
        evaluation_id=evaluation_id,
        decision=decision,
        risk_score=scoring.composite_score,
        risk_percent=round(scoring.composite_score * 100),
        risk_level=_risk_level(scoring.composite_score),
        summary=_build_summary(decision, results),
        indicators=indicators,
        scoring=ScoringDetail(
            composite_score=scoring.composite_score,
            decision=scoring.decision,
            reasoning=scoring.reasoning,
            weighted_breakdown={
                INDICATOR_DISPLAY_NAMES.get(k, k): v
                for k, v in scoring.weighted_breakdown.items()
            },
            has_hard_escalation=has_hard,
            has_multi_critical=has_multi,
        ),
        gray_zone=None,
        llm_comparison=None,
        elapsed_s=elapsed,
        checked_at=datetime.now(timezone.utc),
    )


def _build_indicator_details(
    results: list[IndicatorResult],
) -> list[IndicatorDetail]:
    """Convert raw indicator results to sorted frontend details."""
    return sorted(
        [
            IndicatorDetail(
                name=r.indicator_name,
                display_name=INDICATOR_DISPLAY_NAMES.get(
                    r.indicator_name, r.indicator_name,
                ),
                score=r.score,
                confidence=r.confidence,
                weight=INDICATOR_WEIGHTS.get(r.indicator_name, 1.0),
                weighted_score=round(
                    r.score * INDICATOR_WEIGHTS.get(r.indicator_name, 1.0), 4
                ),
                reasoning=r.reasoning,
                evidence=r.evidence,
                status=_classify_status(r.score),
            )
            for r in results
        ],
        key=lambda i: (_STATUS_PRIORITY.get(i.status, 2), -i.weighted_score),
    )[:5]


def _classify_status(score: float) -> str:
    if score < 0.3:
        return "pass"
    if score < 0.6:
        return "warn"
    return "fail"


def _risk_level(score: float) -> str:
    if score < 0.30:
        return "low"
    if score < 0.70:
        return "medium"
    return "high"


def _build_summary(
    decision: str,
    results: list[IndicatorResult],
) -> str:
    """Build plain-English summary without numeric scores."""
    decision_phrases = {
        "approved": "This withdrawal was approved with no significant risk indicators",
        "escalated": "This withdrawal was escalated for manual review",
        "blocked": "This withdrawal was blocked",
    }
    base = decision_phrases.get(decision, "This withdrawal was reviewed")

    flagged = sorted(
        [r for r in results if r.score > 0],
        key=lambda r: r.score,
        reverse=True,
    )
    if not flagged:
        return f"{base}."

    first_sentence = flagged[0].reasoning.split(". ")[0]
    if not first_sentence.endswith("."):
        first_sentence += "."
    return f"{base}. {first_sentence}"
