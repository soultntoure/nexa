"""Amount Anomaly indicator — z-score of withdrawal amount vs history."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.withdrawal_repository import WithdrawalRepository


class AmountAnomalyIndicator(BaseIndicator):
    name = "amount_anomaly"
    weight = 1.0

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        amount = float(ctx.get("amount", 0))
        repo = WithdrawalRepository(session)
        row = await repo.get_amount_stats(ctx["customer_id"])

        avg = float(row["avg_amt"])
        std = float(row["std_amt"])
        count = int(row["total_count"])

        score, reasoning, evidence = _compute_score(amount, avg, std, count)
        return IndicatorResult(
            indicator_name="amount_anomaly",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(
    amount: float, avg: float, std: float, count: int,
) -> tuple[float, str, dict]:
    """Map z-score to 0-1 risk band."""
    if count < 2 or std == 0:
        score = 0.3 if count == 0 else 0.15
        evidence = {"avg": avg, "std": std, "count": count, "z_score": None}
        from app.core.indicators._reasoning import build_amount_reasoning
        reasoning = build_amount_reasoning(evidence, score, amount)
        return score, reasoning, evidence

    z = (amount - avg) / std
    evidence = {"avg": avg, "std": std, "count": count, "z_score": round(z, 2)}

    if z <= 1.0:
        score = 0.0
    elif z <= 2.0:
        score = 0.25
    elif z <= 3.0:
        score = 0.40
    else:
        score = min(0.75, 0.40 + (z - 3.0) * 0.08)

    from app.core.indicators._reasoning import build_amount_reasoning
    reasoning = build_amount_reasoning(evidence, score, amount)
    return score, reasoning, evidence
