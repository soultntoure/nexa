"""Detector: rapid deposit-then-withdrawal cycles within tight time windows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.detectors.base import PatternMatchResult


class RapidFundingCycleDetector:
    """Window functions to find deposit → withdrawal cycles within 6 hours."""

    pattern_type = "rapid_funding_cycle"

    async def detect(self, session: AsyncSession) -> list[PatternMatchResult]:
        result = await session.execute(
            text("""
                WITH deposit_events AS (
                    SELECT
                        customer_id,
                        amount,
                        timestamp AS event_time,
                        'deposit' AS event_type
                    FROM transactions
                    WHERE type = 'deposit'
                ),
                withdrawal_events AS (
                    SELECT
                        customer_id,
                        amount,
                        created_at AS event_time,
                        'withdrawal' AS event_type
                    FROM withdrawals
                ),
                all_events AS (
                    SELECT * FROM deposit_events
                    UNION ALL
                    SELECT * FROM withdrawal_events
                ),
                sequenced AS (
                    SELECT
                        customer_id,
                        event_type,
                        event_time,
                        amount,
                        LAG(event_type) OVER (
                            PARTITION BY customer_id ORDER BY event_time
                        ) AS prev_type,
                        LAG(event_time) OVER (
                            PARTITION BY customer_id ORDER BY event_time
                        ) AS prev_time,
                        LAG(amount) OVER (
                            PARTITION BY customer_id ORDER BY event_time
                        ) AS prev_amount
                    FROM all_events
                ),
                cycles AS (
                    SELECT
                        customer_id,
                        prev_time AS deposit_time,
                        event_time AS withdrawal_time,
                        EXTRACT(EPOCH FROM (event_time - prev_time)) / 3600.0
                            AS cycle_hours,
                        amount AS withdrawal_amount,
                        prev_amount AS deposit_amount
                    FROM sequenced
                    WHERE event_type = 'withdrawal'
                      AND prev_type = 'deposit'
                      AND EXTRACT(EPOCH FROM (event_time - prev_time)) / 3600.0 <= 6
                ),
                customer_cycles AS (
                    SELECT
                        customer_id,
                        COUNT(*) AS cycle_count,
                        AVG(cycle_hours) AS avg_cycle_hours,
                        SUM(withdrawal_amount) AS total_cycled_amount,
                        COUNT(DISTINCT DATE(deposit_time)) AS distinct_days
                    FROM cycles
                    GROUP BY customer_id
                    HAVING COUNT(*) >= 2
                )
                SELECT * FROM customer_cycles
            """),
        )

        matches: list[PatternMatchResult] = []
        for row in result.mappings():
            cycle_count = int(row["cycle_count"])
            avg_hours = float(row["avg_cycle_hours"])
            total_amount = float(row["total_cycled_amount"])

            confidence = min(0.95, 0.6 + cycle_count * 0.1)

            matches.append(
                PatternMatchResult(
                    customer_id=UUID(str(row["customer_id"])),
                    confidence=round(confidence, 4),
                    evidence={
                        "cycle_count": cycle_count,
                        "avg_cycle_duration_hours": round(avg_hours, 2),
                        "total_cycled_amount": round(total_amount, 2),
                        "distinct_days": int(row["distinct_days"]),
                    },
                    group_key=None,
                ),
            )

        return matches
