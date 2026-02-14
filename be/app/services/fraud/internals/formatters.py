"""Context builders for fraud pipelines."""

from app.agentic_system.schemas.indicators import IndicatorResult
from app.agentic_system.schemas.triage import InvestigatorResult
from app.api.schemas.fraud.fraud_check import FraudCheckRequest
from app.core.scoring import ScoringResult


def build_rule_ctx(request: FraudCheckRequest) -> dict:
    """Extract rule-engine context from a fraud check request."""
    return {
        "customer_id": request.customer_id,
        "amount": request.amount,
        "recipient_name": request.recipient_name,
        "recipient_account": request.recipient_account,
        "ip_address": request.ip_address,
        "device_fingerprint": request.device_fingerprint,
        "customer_country": request.customer_country,
    }


def format_indicators_for_llm(
    results: list[IndicatorResult],
    scoring: ScoringResult,
    request: FraudCheckRequest,
) -> str:
    """Format indicator results as LLM-readable text for triage/investigation."""
    lines = [
        "Withdrawal request:",
        f"- customer_id: {request.customer_id}",
        f"- amount: {request.amount}",
        f"- ip_address: {request.ip_address}",
        f"- customer_country: {request.customer_country}",
        f"\n## Composite Score: {scoring.composite_score} (GRAY ZONE)",
        "\n## Indicator Scores",
    ]
    for r in results:
        lines.append(
            f"- {r.indicator_name}: score={r.score} "
            f"confidence={r.confidence} | {r.reasoning}"
        )
    lines.append(
        "\nInvestigate the top suspicious indicators "
        "and decide: approved or blocked."
    )
    return "\n".join(lines)


def format_investigators_for_verdict(findings: list[dict]) -> str:
    """Format investigator results as LLM-readable text for triage verdict."""
    sections: list[str] = ["## Investigator Reports\n"]

    for f in findings:
        result: InvestigatorResult | None = f.get("result")
        if result is None:
            name = f.get("name", "unknown")
            sections.append(f"### {name}\nFailed — no result available.\n")
            continue

        sections.append(
            f"### {result.investigator_name} "
            f"(score: {result.score:.2f}, confidence: {result.confidence:.2f})"
        )
        sections.append(f"Reasoning: {result.reasoning}")
        if result.evidence:
            evidence_str = ", ".join(
                f"{k}: {v}" for k, v in result.evidence.items()
            )
            sections.append(f"Evidence: {{{evidence_str}}}")
        sections.append("")

    return "\n".join(sections)
