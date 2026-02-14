"""Format posture and pattern data as LLM prompt context."""

from app.data.db.models.customer_risk_posture import CustomerRiskPosture


def format_posture_context(posture: CustomerRiskPosture) -> str:
    """Build posture context text for triage/investigator LLM prompts.

    Always injected regardless of POSTURE_INFLUENCE_ENABLED.
    """
    evidence = posture.signal_evidence or {}
    top_reasons = evidence.get("top_reasons", [])

    lines = [
        "\n## Pre-Fraud Posture",
        f"State: {posture.posture}",
        f"Score: {posture.composite_score:.2f}",
    ]
    if top_reasons:
        lines.append("Top reasons:")
        for reason in top_reasons:
            lines.append(f"- {reason}")

    return "\n".join(lines)


def format_pattern_context(matches: list) -> str:
    """Build pattern match context text for triage/investigator LLM prompts."""
    if not matches:
        return ""

    lines = ["\n## Active Pattern Matches\n"]
    lines.append(f"Customer matches {len(matches)} active fraud pattern(s):\n")

    for i, m in enumerate(matches, 1):
        lines.append(f"{i}. **{m.pattern.pattern_type}** (confidence: {m.confidence:.2f})")
        lines.append(f"   {m.pattern.description}")
        if "ring_size" in m.evidence:
            lines.append(f"   Ring size: {m.evidence['ring_size']} accounts")
        if "linked_customers" in m.evidence:
            lines.append(f"   Linked accounts: {', '.join(m.evidence['linked_customers'])}")
        lines.append("")

    return "\n".join(lines)
