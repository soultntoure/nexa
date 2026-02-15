"""Aggregate indicator scores into a final approve/escalate/block decision."""

from dataclasses import dataclass, field
from typing import Literal

from app.agentic_system.schemas.indicators import IndicatorResult

Decision = Literal["approved", "escalated", "blocked"]

APPROVE_THRESHOLD = 0.30
BLOCK_THRESHOLD = 0.70
HARD_ESCALATION_THRESHOLD = 0.80

# Critical: 2+ indicators above this triggers auto-block
MULTI_CRITICAL_THRESHOLD = 0.6
MULTI_CRITICAL_COUNT = 4

# Concentrated risk: top-3 weighted scores summing above this force escalation.
# Catches cases where 2-3 moderate signals converge but composite is diluted.
CONCENTRATED_ESCALATION_THRESHOLD = 0.90
CONCENTRATED_TOP_N = 3

INDICATOR_WEIGHTS: dict[str, float] = {
    "geographic": 1.0,
    "trading_behavior": 1.5,
    "device_fingerprint": 1.3,
    "card_errors": 1.2,
    "amount_anomaly": 1.0,
    "velocity": 1.0,
    "payment_method": 1.0,
    "recipient": 1.0,
}


@dataclass(frozen=True)
class ScoringResult:
    """Final scoring output from the rule engine."""

    decision: Decision
    composite_score: float
    weighted_breakdown: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


def calculate_risk_score(
    results: list[IndicatorResult],
    weights: dict[str, float] | None = None,
    approve_threshold: float = APPROVE_THRESHOLD,
    block_threshold: float = BLOCK_THRESHOLD,
) -> ScoringResult:
    """Compute weighted average risk score and decision from indicator results."""
    if weights is None:
        weights = INDICATOR_WEIGHTS

    if not results:
        return ScoringResult(
            decision="escalated",
            composite_score=0.0,
            reasoning="No indicator results available.",
        )

    breakdown = _build_weighted_breakdown(results, weights)
    composite = _compute_composite(breakdown, weights)
    has_critical = _check_hard_escalation(results)
    has_multi_critical = _check_multi_critical(results)
    has_concentrated = _check_concentrated_risk(breakdown)
    decision = _determine_decision(
        composite, has_critical, has_multi_critical,
        approve_threshold, block_threshold,
        has_concentrated=has_concentrated,
    )
    # Ensure displayed score aligns with decision when overrides fire
    display_score = _align_score_with_decision(
        composite, decision, approve_threshold, block_threshold,
    )
    reasoning = _build_reasoning(
        breakdown, decision, display_score,
        has_critical, has_multi_critical, has_concentrated,
    )

    return ScoringResult(
        decision=decision,
        composite_score=round(display_score, 4),
        weighted_breakdown=breakdown,
        reasoning=reasoning,
    )


def _build_weighted_breakdown(
    results: list[IndicatorResult], weights: dict[str, float],
) -> dict[str, float]:
    """Map each indicator to its weighted score."""
    return {
        r.indicator_name: r.score * weights.get(r.indicator_name, 1.0)
        for r in results
    }


def _compute_composite(
    breakdown: dict[str, float], weights: dict[str, float],
) -> float:
    """Weighted average normalized by total weight."""
    total_weight = sum(
        weights.get(name, 1.0) for name in breakdown
    )
    if total_weight == 0:
        return 0.0
    raw = sum(breakdown.values())
    return raw / total_weight


def _check_hard_escalation(results: list[IndicatorResult]) -> bool:
    """Any single indicator >= 0.80 with confidence >= 0.8 forces escalation."""
    return any(
        r.score >= HARD_ESCALATION_THRESHOLD and r.confidence >= 0.8
        for r in results
    )


def _check_multi_critical(results: list[IndicatorResult]) -> bool:
    """2+ indicators >= 0.6 forces auto-block (fraud ring / multi-signal)."""
    count = sum(
        1 for r in results
        if r.score >= MULTI_CRITICAL_THRESHOLD and r.confidence >= 0.8
    )
    return count >= MULTI_CRITICAL_COUNT


def _check_concentrated_risk(
    breakdown: dict[str, float],
) -> bool:
    """Top-N weighted scores summing above threshold forces escalation.

    Catches converging moderate signals that get diluted in the full average.
    """
    top = sorted(breakdown.values(), reverse=True)[:CONCENTRATED_TOP_N]
    return sum(top) >= CONCENTRATED_ESCALATION_THRESHOLD


def _determine_decision(
    composite: float,
    has_critical: bool,
    has_multi_critical: bool,
    approve_threshold: float = APPROVE_THRESHOLD,
    block_threshold: float = BLOCK_THRESHOLD,
    has_concentrated: bool = False,
) -> Decision:
    """Apply threshold logic with escalation overrides."""
    if composite >= block_threshold or has_multi_critical:
        return "blocked"
    if composite >= approve_threshold or has_critical or has_concentrated:
        return "escalated"
    return "approved"


def _align_score_with_decision(
    composite: float,
    decision: Decision,
    approve_threshold: float = APPROVE_THRESHOLD,
    block_threshold: float = BLOCK_THRESHOLD,
) -> float:
    """Ensure the displayed score is at least as high as the decision threshold.

    When multi-critical or hard-escalation overrides bump the decision above
    what the composite alone would produce, the displayed score should reflect
    the severity so it doesn't look contradictory (e.g. 33% but blocked).
    """
    if decision == "blocked":
        return max(composite, block_threshold)
    if decision == "escalated":
        return max(composite, approve_threshold)
    return composite


INDICATOR_LABELS: dict[str, str] = {
    "trading_behavior": "trading activity",
    "device_fingerprint": "device recognition",
    "geographic": "geographic signals",
    "amount_anomaly": "withdrawal amount",
    "velocity": "withdrawal frequency",
    "payment_method": "payment method",
    "recipient": "recipient analysis",
    "card_errors": "transaction error history",
}


def _build_reasoning(
    breakdown: dict[str, float],
    decision: Decision,
    composite: float,
    has_critical: bool,
    has_multi_critical: bool,
    has_concentrated: bool = False,
) -> str:
    """Build plain-English reasoning without numeric scores."""
    decision_text = {
        "approved": "This withdrawal was approved",
        "escalated": "This withdrawal was escalated for manual review",
        "blocked": "This withdrawal was blocked",
    }[decision]

    top = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    significant = [(n, s) for n, s in top if s > 0]

    if not significant:
        return f"{decision_text}. No risk indicators were flagged."

    parts = [decision_text + "."]
    primary_name, _ = significant[0]
    primary_label = INDICATOR_LABELS.get(primary_name, primary_name)
    parts.append(f"The customer's {primary_label} is the primary concern.")

    if len(significant) > 1:
        secondary = [
            INDICATOR_LABELS.get(n, n) for n, _ in significant[1:3]
        ]
        if len(secondary) == 1:
            parts.append(f"Additionally, {secondary[0]} was flagged.")
        else:
            parts.append(
                f"Additionally, {secondary[0]} and {secondary[1]} were flagged."
            )

    if has_multi_critical:
        parts.append(
            "Multiple indicators flagged significant risk, "
            "triggering automatic block."
        )
    elif has_critical:
        parts.append(
            "One indicator exceeded the critical threshold, "
            "triggering automatic escalation."
        )
    elif has_concentrated:
        parts.append(
            "Several indicators show concentrated risk, "
            "triggering automatic escalation."
        )

    return " ".join(parts)
