"""Payment Method Risk indicator — method age, verification, blacklist."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.payment_method_repository import PaymentMethodRepository


class PaymentMethodIndicator(BaseIndicator):
    name = "payment_method"
    weight = 1.0

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        repo = PaymentMethodRepository(session)
        row = await repo.get_latest_method_risk(ctx["customer_id"])

        if not row:
            return IndicatorResult(
                indicator_name="payment_method",
                score=0.3,
                confidence=1.0,
                reasoning="No payment method is on file for this customer, which prevents verification.",
                evidence={},
            )

        score, reasoning, evidence = _compute_score(row)
        return IndicatorResult(
            indicator_name="payment_method",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(row: dict) -> tuple[float, str, dict]:
    """Score based on method age, verification, blacklist, churn."""
    age_days = float(row["age_days"] or 0)
    is_verified = bool(row["is_verified"])
    is_blacklisted = bool(row["is_blacklisted"])
    churn_30d = int(row["methods_added_30d"] or 0)

    evidence = {
        "age_days": round(age_days, 1),
        "is_verified": is_verified,
        "is_blacklisted": is_blacklisted,
        "methods_added_30d": churn_30d,
    }

    score = 0.0
    reasons = []

    if is_blacklisted:
        score += 0.5
        reasons.append("Blacklisted method")
    if not is_verified:
        score += 0.2
        reasons.append("Unverified")
    if age_days < 7:
        score += 0.3
        reasons.append(f"New method ({age_days:.0f}d old)")
    elif age_days < 30:
        score += 0.1
        reasons.append(f"Recent method ({age_days:.0f}d old)")
    if churn_30d >= 3:
        score += 0.2
        reasons.append(f"{churn_30d} methods added in 30d")

    score = min(score, 1.0)
    from app.core.indicators._reasoning import build_payment_method_reasoning
    reasoning = build_payment_method_reasoning(evidence, round(score, 2), reasons)
    return round(score, 2), reasoning, evidence
