"""Card Error History indicator — recent failures and method switching."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.transaction_repository import TransactionRepository


class CardErrorsIndicator(BaseIndicator):
    name = "card_errors"
    weight = 1.2

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        repo = TransactionRepository(session)
        row = await repo.get_card_error_stats(ctx["customer_id"])

        fails = int(row["fail_count_30d"])
        errors = int(row["error_count_30d"])
        methods = int(row["distinct_methods_30d"])

        score, reasoning, evidence = _compute_score(fails, errors, methods)
        return IndicatorResult(
            indicator_name="card_errors",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(
    fails: int, errors: int, methods: int,
) -> tuple[float, str, dict]:
    """Score based on failure count, error codes, and method switching."""
    evidence = {
        "fail_count_30d": fails,
        "error_count_30d": errors,
        "distinct_methods_30d": methods,
    }

    score = 0.0
    reasons = []

    if fails >= 5:
        score += 0.5
        reasons.append(f"{fails} failed transactions in 30d")
    elif fails >= 2:
        score += 0.2
        reasons.append(f"{fails} failed transactions in 30d")

    if methods >= 4:
        score += 0.4
        reasons.append(f"{methods} payment methods used in 30d (switching)")
    elif methods >= 3:
        score += 0.2
        reasons.append(f"{methods} payment methods used in 30d")

    score = min(score, 1.0)
    from app.core.indicators._reasoning import build_card_errors_reasoning
    return round(score, 2), build_card_errors_reasoning(evidence, round(score, 2)), evidence
