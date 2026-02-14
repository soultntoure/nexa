"""
Account Maturity signal — flags new, inactive, or recently-reactivated accounts.

Sub-signals:
- Account age: >= 180d safe, <= 7d risky
- Total trade count: >= 50 safe, 0 risky
- Activity density (trades/month): >= 10/month safe, < 1/month risky
- Dormancy gap (longest inactive period in last 180d): 0d safe, >= 90d risky

Inputs: customers, trades
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.signals.base import BaseSignal, SignalResult, _linear_score


class AccountMaturitySignal(BaseSignal):
    """Scores account age, trade activity, and dormancy patterns."""

    name = "account_maturity"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        row = await _fetch_maturity_data(customer_id, session)
        score, evidence, reason = _compute_score(row)
        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )


async def _fetch_maturity_data(
    customer_id: uuid.UUID, session: AsyncSession,
) -> dict:
    """Fetch account age, trade counts, and dormancy data."""
    result = await session.execute(
        text("""
            SELECT
                EXTRACT(EPOCH FROM (NOW() - c.registration_date)) / 86400.0
                    AS account_age_days,
                COUNT(t.id) AS total_trades,
                EXTRACT(EPOCH FROM (NOW() - c.registration_date)) / (86400.0 * 30.0)
                    AS account_age_months
            FROM customers c
            LEFT JOIN trades t ON t.customer_id = c.id
            WHERE c.id = :cid
            GROUP BY c.id, c.registration_date
        """),
        {"cid": customer_id},
    )
    row = result.mappings().first()
    if not row:
        return {
            "account_age_days": 0,
            "total_trades": 0,
            "account_age_months": 0,
            "dormancy_gap_days": 0,
        }

    data = dict(row)

    # Compute dormancy gap: longest gap between consecutive trades in last 180d
    gap_result = await session.execute(
        text("""
            WITH trade_dates AS (
                SELECT opened_at AS ts
                FROM trades
                WHERE customer_id = :cid
                  AND opened_at >= NOW() - INTERVAL '180 days'
                ORDER BY opened_at
            ),
            gaps AS (
                SELECT
                    EXTRACT(EPOCH FROM (
                        LEAD(ts) OVER (ORDER BY ts) - ts
                    )) / 86400.0 AS gap_days
                FROM trade_dates
            )
            SELECT COALESCE(MAX(gap_days), 0) AS dormancy_gap_days
            FROM gaps
        """),
        {"cid": customer_id},
    )
    gap_row = gap_result.mappings().first()
    data["dormancy_gap_days"] = float(gap_row["dormancy_gap_days"]) if gap_row else 0

    return data


def _compute_score(row: dict) -> tuple[float, dict, str]:
    """Score account maturity from sub-signals."""
    age_days = float(row.get("account_age_days", 0))
    total_trades = int(row.get("total_trades", 0))
    age_months = float(row.get("account_age_months", 0)) or 1.0
    dormancy_gap = float(row.get("dormancy_gap_days", 0))

    # Sub-signal scores (0.0 = safe, 1.0 = risky)
    age_score = _linear_score(age_days, 180.0, 7.0)
    trade_score = _linear_score(total_trades, 50.0, 0.0)
    density = total_trades / age_months if age_months > 0 else 0
    density_score = _linear_score(density, 10.0, 1.0)
    dormancy_score = _linear_score(dormancy_gap, 0.0, 90.0)

    # Weighted average of sub-signals
    score = round(
        (age_score * 0.3 + trade_score * 0.25
         + density_score * 0.25 + dormancy_score * 0.2),
        4,
    )

    evidence = {
        "account_age_days": round(age_days, 1),
        "total_trades": total_trades,
        "activity_density": round(density, 2),
        "dormancy_gap_days": round(dormancy_gap, 1),
    }

    reason = _build_reason(age_days, total_trades, density, dormancy_gap)

    return score, evidence, reason


def _build_reason(
    age_days: float,
    total_trades: int,
    density: float,
    dormancy_gap: float,
) -> str:
    """Build plain-English explanation."""
    parts: list[str] = []

    if age_days <= 7:
        parts.append(f"Very new account ({age_days:.0f} days old)")
    elif age_days <= 30:
        parts.append(f"Account is {age_days:.0f} days old")

    if total_trades == 0:
        parts.append("no trading history")
    elif total_trades < 10:
        parts.append(f"limited trading ({total_trades} trades)")

    if density < 1 and total_trades > 0:
        parts.append(f"low activity density ({density:.1f}/month)")

    if dormancy_gap >= 30:
        parts.append(f"{dormancy_gap:.0f}-day dormancy gap")

    if not parts:
        return "Mature account with consistent activity"

    return "; ".join(parts)
