"""Trading Behavior indicator — deposit-to-withdrawal ratio and activity."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.transaction_repository import TransactionRepository


class TradingBehaviorIndicator(BaseIndicator):
    name = "trading_behavior"
    weight = 1.5

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        repo = TransactionRepository(session)
        row = await repo.get_trading_behavior_stats(ctx["customer_id"])

        amount = float(ctx.get("amount", 0))
        deposits = float(row["total_deposits"])
        trades = int(row["trade_count"])
        pnl = float(row["total_pnl"])

        score, reasoning, evidence = _compute_score(
            amount, deposits, trades, pnl,
        )
        return IndicatorResult(
            indicator_name="trading_behavior",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(
    amount: float, deposits: float, trades: int, pnl: float,
) -> tuple[float, str, dict]:
    """Score: no trades + high withdrawal = suspicious."""
    ratio = amount / deposits if deposits > 0 else 999.0
    evidence = {
        "total_deposits": deposits,
        "trade_count": trades,
        "total_pnl": pnl,
        "withdraw_deposit_ratio": round(ratio, 2),
    }

    score = 0.0
    reasons = []

    # No trading at all — "deposit and run"
    if trades == 0:
        score += 0.6
        reasons.append("Zero trades on account")
    elif trades < 3:
        score += 0.35
        reasons.append(f"Minimal trading ({trades} trades)")
    elif trades < 5:
        score += 0.15
        reasons.append(f"Low trading ({trades} trades)")

    # High withdrawal-to-deposit ratio
    if ratio >= 0.9:
        score += 0.4
        reasons.append(f"Withdrawing {ratio:.0%} of deposits")
    elif ratio >= 0.7:
        score += 0.25
        reasons.append(f"Withdrawing {ratio:.0%} of deposits")

    score = min(score, 1.0)
    from app.core.indicators._reasoning import build_trading_reasoning
    return round(score, 2), build_trading_reasoning(evidence, round(score, 2), amount), evidence
