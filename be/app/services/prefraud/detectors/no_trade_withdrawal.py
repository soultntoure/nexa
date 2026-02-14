"""Detector: accounts with age < 7d, zero trades, withdrawal > 90% of deposits."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.detectors.base import PatternMatchResult


class NoTradeWithdrawalDetector:
    """SQL aggregation + HAVING to find no-trade withdrawal patterns."""

    pattern_type = "no_trade_withdrawal"

    async def detect(self, session: AsyncSession) -> list[PatternMatchResult]:
        result = await session.execute(
            text("""
                SELECT
                    c.id AS customer_id,
                    EXTRACT(DAY FROM NOW() - c.created_at) AS account_age_days,
                    COALESCE(t.trade_count, 0) AS trade_count,
                    COALESCE(dep.total_deposited, 0) AS total_deposited,
                    COALESCE(wd.total_withdrawn, 0) AS total_withdrawn
                FROM customers c
                LEFT JOIN (
                    SELECT customer_id, COUNT(*) AS trade_count
                    FROM trades
                    GROUP BY customer_id
                ) t ON t.customer_id = c.id
                LEFT JOIN (
                    SELECT customer_id, SUM(amount) AS total_deposited
                    FROM transactions
                    WHERE type = 'deposit'
                    GROUP BY customer_id
                ) dep ON dep.customer_id = c.id
                LEFT JOIN (
                    SELECT customer_id, SUM(amount) AS total_withdrawn
                    FROM withdrawals
                    GROUP BY customer_id
                ) wd ON wd.customer_id = c.id
                WHERE c.created_at >= NOW() - INTERVAL '7 days'
                GROUP BY c.id, c.created_at,
                         t.trade_count, dep.total_deposited, wd.total_withdrawn
                HAVING COALESCE(t.trade_count, 0) = 0
                   AND COALESCE(dep.total_deposited, 0) > 0
                   AND COALESCE(wd.total_withdrawn, 0)
                       / NULLIF(COALESCE(dep.total_deposited, 0), 0) >= 0.9
            """),
        )

        matches: list[PatternMatchResult] = []
        for row in result.mappings():
            deposited = float(row["total_deposited"])
            withdrawn = float(row["total_withdrawn"])
            ratio = withdrawn / deposited if deposited > 0 else 0.0
            age = float(row["account_age_days"])

            confidence = min(0.95, 0.7 + (ratio - 0.9) * 2.5)

            matches.append(
                PatternMatchResult(
                    customer_id=UUID(str(row["customer_id"])),
                    confidence=round(confidence, 4),
                    evidence={
                        "account_age_days": round(age, 1),
                        "trade_count": int(row["trade_count"]),
                        "withdrawal_to_deposit_ratio": round(ratio, 4),
                        "total_withdrawn": round(withdrawn, 2),
                        "total_deposited": round(deposited, 2),
                    },
                    group_key=None,
                ),
            )

        return matches
