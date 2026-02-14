"""Map triage verdict to final decision with guardrails."""

from app.agentic_system.schemas.triage import TriageResult
from app.core.scoring import APPROVE_THRESHOLD, ScoringResult


def apply_verdict(
    scoring: ScoringResult,
    triage: TriageResult,
    posture_uplift: float = 0.0,
    approve_threshold: float = APPROVE_THRESHOLD,
) -> tuple[str, float]:
    """Map triage verdict to final decision with guardrails.

    Guardrails:
    - Auto-decided cases (no investigators): use rule engine decision directly.
    - Rule engine blocked + triage approved: override to escalated (safety net).
    - Low-confidence triage (<0.5): fall back to rule engine decision.
    - Otherwise: triage verdict is authoritative.
    """
    adjusted_rule = scoring.composite_score + posture_uplift

    # No investigators ran (auto-decide cases)
    if not triage.assignments:
        return scoring.decision, adjusted_rule

    # Guardrail: rule-blocked cannot be approved by triage
    if scoring.decision == "blocked" and triage.decision == "approved":
        return "escalated", max(triage.risk_score, adjusted_rule)

    # Low-confidence verdict: fall back to rule engine
    if triage.confidence < 0.5:
        return scoring.decision, adjusted_rule

    # Triage verdict is authoritative
    return triage.decision, triage.risk_score
