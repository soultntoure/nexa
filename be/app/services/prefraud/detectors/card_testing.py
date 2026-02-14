"""Detector: sequential failed deposits → success → immediate withdrawal."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.detectors.base import PatternMatchResult


class CardTestingDetector:
    """Window functions + LAG/LEAD to find card testing sequences."""

    pattern_type = "card_testing_sequence"

    async def detect(self, session: AsyncSession) -> list[PatternMatchResult]:
        result = await session.execute(
            text("""
                WITH deposit_sequence AS (
                    SELECT
                        customer_id,
                        status,
                        amount,
                        timestamp,
                        LAG(status) OVER (
                            PARTITION BY customer_id ORDER BY timestamp
                        ) AS prev_status,
                        LAG(timestamp) OVER (
                            PARTITION BY customer_id ORDER BY timestamp
                        ) AS prev_time,
                        LEAD(status) OVER (
                            PARTITION BY customer_id ORDER BY timestamp
                        ) AS next_status
                    FROM transactions
                    WHERE type = 'deposit'
                ),
                failed_runs AS (
                    SELECT
                        customer_id,
                        timestamp AS success_time,
                        amount AS success_amount,
                        COUNT(*) OVER (
                            PARTITION BY customer_id
                            ORDER BY timestamp
                            RANGE BETWEEN INTERVAL '6 hours' PRECEDING
                                      AND CURRENT ROW
                        ) AS attempts_in_window
                    FROM deposit_sequence
                    WHERE status = 'success'
                      AND prev_status = 'failed'
                ),
                with_withdrawal AS (
                    SELECT
                        fr.customer_id,
                        fr.success_time,
                        fr.success_amount,
                        fr.attempts_in_window,
                        w.created_at AS withdrawal_time,
                        w.amount AS withdrawal_amount,
                        EXTRACT(EPOCH FROM (w.created_at - fr.success_time))
                            / 3600.0 AS hours_to_withdrawal
                    FROM failed_runs fr
                    JOIN LATERAL (
                        SELECT created_at, amount
                        FROM withdrawals
                        WHERE customer_id = fr.customer_id
                          AND created_at > fr.success_time
                          AND created_at <= fr.success_time + INTERVAL '4 hours'
                        ORDER BY created_at
                        LIMIT 1
                    ) w ON TRUE
                ),
                customer_summary AS (
                    SELECT
                        customer_id,
                        COUNT(*) AS sequence_count,
                        SUM(attempts_in_window) AS total_failed_attempts,
                        AVG(hours_to_withdrawal) AS avg_hours_to_withdrawal,
                        SUM(withdrawal_amount) AS total_withdrawal_amount
                    FROM with_withdrawal
                    GROUP BY customer_id
                )
                SELECT * FROM customer_summary
            """),
        )

        matches: list[PatternMatchResult] = []
        for row in result.mappings():
            failed_count = int(row["total_failed_attempts"])
            seq_count = int(row["sequence_count"])
            avg_hours = float(row["avg_hours_to_withdrawal"])
            total_withdrawn = float(row["total_withdrawal_amount"])

            confidence = min(0.95, 0.6 + seq_count * 0.15)

            matches.append(
                PatternMatchResult(
                    customer_id=UUID(str(row["customer_id"])),
                    confidence=round(confidence, 4),
                    evidence={
                        "failed_attempt_count": failed_count,
                        "success_then_withdrawal": True,
                        "time_span_hours": round(avg_hours, 2),
                        "withdrawal_amount": round(total_withdrawn, 2),
                        "sequence_count": seq_count,
                    },
                    group_key=None,
                ),
            )

        return matches
