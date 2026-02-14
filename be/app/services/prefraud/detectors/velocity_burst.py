"""Detector: 4+ withdrawals within a 1-hour sliding window."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.detectors.base import PatternMatchResult


class VelocityBurstDetector:
    """Window functions + COUNT to find withdrawal velocity bursts."""

    pattern_type = "velocity_burst"

    async def detect(self, session: AsyncSession) -> list[PatternMatchResult]:
        result = await session.execute(
            text("""
                WITH windowed AS (
                    SELECT
                        customer_id,
                        created_at AS withdrawal_time,
                        amount,
                        COUNT(*) OVER (
                            PARTITION BY customer_id
                            ORDER BY created_at
                            RANGE BETWEEN INTERVAL '1 hour' PRECEDING
                                      AND CURRENT ROW
                        ) AS count_in_window,
                        SUM(amount) OVER (
                            PARTITION BY customer_id
                            ORDER BY created_at
                            RANGE BETWEEN INTERVAL '1 hour' PRECEDING
                                      AND CURRENT ROW
                        ) AS sum_in_window,
                        MIN(created_at) OVER (
                            PARTITION BY customer_id
                            ORDER BY created_at
                            RANGE BETWEEN INTERVAL '1 hour' PRECEDING
                                      AND CURRENT ROW
                        ) AS window_start
                    FROM withdrawals
                ),
                bursts AS (
                    SELECT
                        customer_id,
                        MAX(count_in_window) AS max_withdrawal_count_1h,
                        MAX(sum_in_window) AS peak_total_amount,
                        MIN(window_start) AS peak_window_start
                    FROM windowed
                    WHERE count_in_window >= 4
                    GROUP BY customer_id
                )
                SELECT * FROM bursts
            """),
        )

        matches: list[PatternMatchResult] = []
        for row in result.mappings():
            count = int(row["max_withdrawal_count_1h"])
            total = float(row["peak_total_amount"])
            window_start = row["peak_window_start"]

            confidence = min(0.95, 0.65 + (count - 4) * 0.1)

            matches.append(
                PatternMatchResult(
                    customer_id=UUID(str(row["customer_id"])),
                    confidence=round(confidence, 4),
                    evidence={
                        "withdrawal_count_1h": count,
                        "peak_window_start": window_start.isoformat()
                        if window_start
                        else None,
                        "total_amount": round(total, 2),
                    },
                    group_key=None,
                ),
            )

        return matches
