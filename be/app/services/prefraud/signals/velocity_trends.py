"""
Velocity Trends signal — detects acceleration in account activity vs baseline.

Sub-signals:
- Deposit count ratio (7d vs 30d baseline): <= 1.5 safe, >= 5.0 risky
- Deposit amount ratio (7d vs 30d baseline): <= 1.5 safe, >= 5.0 risky
- Withdrawal count ratio (7d vs 30d baseline): <= 1.5 safe, >= 5.0 risky

Baseline: 30-day rolling average excluding the most recent 7 days.
Edge case: If baseline is zero, any recent activity scores 0.8.

Inputs: transactions, withdrawals
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.signals.base import BaseSignal, SignalResult, _linear_score


class VelocityTrendsSignal(BaseSignal):
    """Scores activity acceleration relative to customer's own baseline."""

    name = "velocity_trends"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        data = await _fetch_velocity_data(customer_id, session)
        score, evidence, reason = _compute_score(data)
        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )


async def _fetch_velocity_data(
    customer_id: uuid.UUID, session: AsyncSession,
) -> dict:
    """Fetch deposit and withdrawal counts/amounts in recent vs baseline windows."""
    result = await session.execute(
        text("""
            SELECT
                -- Deposits in last 7 days
                COUNT(*) FILTER (
                    WHERE t.type = 'deposit'
                      AND t.timestamp >= NOW() - INTERVAL '7 days'
                ) AS deposits_7d_count,
                COALESCE(SUM(t.amount) FILTER (
                    WHERE t.type = 'deposit'
                      AND t.timestamp >= NOW() - INTERVAL '7 days'
                ), 0) AS deposits_7d_amount,

                -- Deposits in baseline window (8-30 days ago)
                COUNT(*) FILTER (
                    WHERE t.type = 'deposit'
                      AND t.timestamp >= NOW() - INTERVAL '30 days'
                      AND t.timestamp < NOW() - INTERVAL '7 days'
                ) AS deposits_baseline_count,
                COALESCE(SUM(t.amount) FILTER (
                    WHERE t.type = 'deposit'
                      AND t.timestamp >= NOW() - INTERVAL '30 days'
                      AND t.timestamp < NOW() - INTERVAL '7 days'
                ), 0) AS deposits_baseline_amount
            FROM transactions t
            WHERE t.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    tx_row = result.mappings().first() or {}

    # Withdrawal velocity
    wd_result = await session.execute(
        text("""
            SELECT
                COUNT(*) FILTER (
                    WHERE w.requested_at >= NOW() - INTERVAL '7 days'
                ) AS withdrawals_7d_count,
                COUNT(*) FILTER (
                    WHERE w.requested_at >= NOW() - INTERVAL '30 days'
                      AND w.requested_at < NOW() - INTERVAL '7 days'
                ) AS withdrawals_baseline_count
            FROM withdrawals w
            WHERE w.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    wd_row = wd_result.mappings().first() or {}

    return {
        "deposits_7d_count": int(tx_row.get("deposits_7d_count", 0)),
        "deposits_7d_amount": float(tx_row.get("deposits_7d_amount", 0)),
        "deposits_baseline_count": int(tx_row.get("deposits_baseline_count", 0)),
        "deposits_baseline_amount": float(tx_row.get("deposits_baseline_amount", 0)),
        "withdrawals_7d_count": int(wd_row.get("withdrawals_7d_count", 0)),
        "withdrawals_baseline_count": int(wd_row.get("withdrawals_baseline_count", 0)),
    }


def _safe_ratio(recent: float, baseline: float) -> tuple[float, bool]:
    """Compute ratio of recent to baseline activity.

    Returns (ratio, is_zero_baseline).
    If baseline is zero but recent > 0, returns (0.0, True) — handled
    separately in scoring (new accounts are inherently velocity-spikey).
    """
    if baseline == 0:
        return (0.0, recent > 0)
    # Normalize baseline to 7-day equivalent (baseline covers 23 days)
    baseline_7d_equiv = baseline * (7.0 / 23.0)
    if baseline_7d_equiv == 0:
        return (0.0, recent > 0)
    return (recent / baseline_7d_equiv, False)


def _compute_score(data: dict) -> tuple[float, dict, str]:
    """Score velocity from deposit/withdrawal ratios vs baseline."""
    dep_count_ratio, dep_count_zero = _safe_ratio(
        data["deposits_7d_count"], data["deposits_baseline_count"],
    )
    dep_amount_ratio, dep_amount_zero = _safe_ratio(
        data["deposits_7d_amount"], data["deposits_baseline_amount"],
    )
    wd_count_ratio, wd_count_zero = _safe_ratio(
        data["withdrawals_7d_count"], data["withdrawals_baseline_count"],
    )

    # Score each sub-signal
    sub_scores: list[float] = []

    if dep_count_zero:
        sub_scores.append(0.8)
    else:
        sub_scores.append(_linear_score(dep_count_ratio, 1.5, 5.0))

    if dep_amount_zero:
        sub_scores.append(0.8)
    else:
        sub_scores.append(_linear_score(dep_amount_ratio, 1.5, 5.0))

    if wd_count_zero:
        sub_scores.append(0.8)
    else:
        sub_scores.append(_linear_score(wd_count_ratio, 1.5, 5.0))

    score = round(sum(sub_scores) / len(sub_scores), 4) if sub_scores else 0.0

    evidence = {
        "deposits_7d_count": data["deposits_7d_count"],
        "deposits_7d_amount": data["deposits_7d_amount"],
        "deposits_baseline_count": data["deposits_baseline_count"],
        "deposits_baseline_amount": data["deposits_baseline_amount"],
        "withdrawals_7d_count": data["withdrawals_7d_count"],
        "withdrawals_baseline_count": data["withdrawals_baseline_count"],
        "deposit_count_ratio": round(dep_count_ratio, 2),
        "deposit_amount_ratio": round(dep_amount_ratio, 2),
        "withdrawal_count_ratio": round(wd_count_ratio, 2),
    }

    reason = _build_reason(
        dep_count_ratio, dep_amount_ratio, wd_count_ratio,
        dep_count_zero, dep_amount_zero, wd_count_zero,
    )

    return score, evidence, reason


def _build_reason(
    dep_count_ratio: float,
    dep_amount_ratio: float,
    wd_count_ratio: float,
    dep_count_zero: bool,
    dep_amount_zero: bool,
    wd_count_zero: bool,
) -> str:
    """Build plain-English explanation."""
    parts: list[str] = []

    if dep_count_zero or dep_amount_zero:
        parts.append("Activity with no prior baseline (new pattern)")

    if dep_count_ratio >= 3.0:
        parts.append(f"Deposit frequency {dep_count_ratio:.1f}x above baseline")
    elif dep_count_ratio >= 1.5:
        parts.append(f"Deposit frequency elevated ({dep_count_ratio:.1f}x)")

    if dep_amount_ratio >= 3.0:
        parts.append(f"Deposit volume {dep_amount_ratio:.1f}x above baseline")

    if wd_count_ratio >= 3.0:
        parts.append(f"Withdrawal frequency {wd_count_ratio:.1f}x above baseline")
    elif wd_count_zero:
        pass  # Already covered by "no prior baseline"

    if not parts:
        return "No velocity spike detected"

    return "; ".join(parts)
