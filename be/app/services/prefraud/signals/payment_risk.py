"""
Payment Method Risk signal — detects method churn, unverified methods, failures.

Sub-signals:
- Method count: 1-2 safe, >= 5 risky
- Average method age: >= 90d safe, <= 7d risky
- Unverified method ratio: 0% safe, >= 50% risky
- Failed transaction rate (30d): 0% safe, >= 30% risky
- Has blacklisted method: no safe, yes risky
- Newest method age: >= 30d safe, <= 1d risky

Inputs: payment_methods, transactions
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.signals.base import BaseSignal, SignalResult, _linear_score


class PaymentRiskSignal(BaseSignal):
    """Scores payment method diversity, verification, and failure patterns."""

    name = "payment_risk"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        data = await _fetch_payment_data(customer_id, session)
        score, evidence, reason = _compute_score(data)
        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )


async def _fetch_payment_data(
    customer_id: uuid.UUID, session: AsyncSession,
) -> dict:
    """Fetch payment method stats and transaction failure rates."""
    pm_result = await session.execute(
        text("""
            SELECT
                COUNT(*) AS method_count,
                COALESCE(
                    AVG(EXTRACT(EPOCH FROM (NOW() - pm.added_at)) / 86400.0),
                    0
                ) AS avg_method_age_days,
                CASE
                    WHEN COUNT(*) = 0 THEN 0
                    ELSE COUNT(*) FILTER (WHERE pm.is_verified = FALSE)::FLOAT
                         / COUNT(*)::FLOAT
                END AS unverified_ratio,
                BOOL_OR(pm.is_blacklisted) AS has_blacklisted,
                COALESCE(
                    MIN(EXTRACT(EPOCH FROM (NOW() - pm.added_at)) / 86400.0),
                    0
                ) AS newest_method_age_days
            FROM payment_methods pm
            WHERE pm.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    pm_row = pm_result.mappings().first() or {}

    tx_result = await session.execute(
        text("""
            SELECT
                COUNT(*) AS total_tx_30d,
                COUNT(*) FILTER (WHERE t.status = 'failed') AS failed_tx_30d
            FROM transactions t
            WHERE t.customer_id = :cid
              AND t.timestamp >= NOW() - INTERVAL '30 days'
        """),
        {"cid": customer_id},
    )
    tx_row = tx_result.mappings().first() or {}

    total_tx = int(tx_row.get("total_tx_30d", 0))
    failed_tx = int(tx_row.get("failed_tx_30d", 0))

    return {
        "method_count": int(pm_row.get("method_count", 0)),
        "avg_method_age_days": float(pm_row.get("avg_method_age_days", 0)),
        "unverified_ratio": float(pm_row.get("unverified_ratio", 0)),
        "has_blacklisted": bool(pm_row.get("has_blacklisted", False)),
        "newest_method_age_days": float(pm_row.get("newest_method_age_days", 0)),
        "failed_tx_rate": (failed_tx / total_tx) if total_tx > 0 else 0.0,
        "failed_tx_count": failed_tx,
    }


def _compute_score(data: dict) -> tuple[float, dict, str]:
    """Score payment risk from sub-signals."""
    method_count = data["method_count"]
    avg_age = data["avg_method_age_days"]
    unverified_ratio = data["unverified_ratio"]
    failed_rate = data["failed_tx_rate"]
    has_blacklisted = data["has_blacklisted"]
    newest_age = data["newest_method_age_days"]

    # No payment methods — can't score
    if method_count == 0:
        return 0.0, data, "No payment methods on file"

    # Sub-signal scores
    count_score = _linear_score(method_count, 2, 5)
    avg_age_score = _linear_score(avg_age, 90.0, 7.0)
    unverified_score = _linear_score(unverified_ratio, 0.0, 0.5)
    failed_score = _linear_score(failed_rate, 0.0, 0.3)
    blacklist_score = 1.0 if has_blacklisted else 0.0
    newest_score = _linear_score(newest_age, 30.0, 1.0)

    # Weighted average
    score = round(
        (count_score * 0.15
         + avg_age_score * 0.15
         + unverified_score * 0.15
         + failed_score * 0.20
         + blacklist_score * 0.20
         + newest_score * 0.15),
        4,
    )

    evidence = {
        "method_count": method_count,
        "avg_method_age_days": round(avg_age, 1),
        "unverified_ratio": round(unverified_ratio, 2),
        "failed_tx_rate": round(failed_rate, 2),
        "has_blacklisted": has_blacklisted,
        "newest_method_age_days": round(newest_age, 1),
    }

    reason = _build_reason(
        method_count, unverified_ratio,
        failed_rate, has_blacklisted, newest_age,
        data["failed_tx_count"],
    )

    return score, evidence, reason


def _build_reason(
    method_count: int,
    unverified_ratio: float,
    failed_rate: float,
    has_blacklisted: bool,
    newest_age: float,
    failed_count: int,
) -> str:
    """Build plain-English explanation."""
    parts: list[str] = []

    if has_blacklisted:
        parts.append("Blacklisted payment method detected")

    if failed_rate >= 0.3:
        parts.append(f"{failed_count} failed transactions in 30d ({failed_rate:.0%} rate)")
    elif failed_rate >= 0.1:
        parts.append(f"Elevated failure rate ({failed_rate:.0%})")

    if method_count >= 5:
        parts.append(f"{method_count} payment methods (high churn)")
    elif method_count >= 3:
        parts.append(f"{method_count} payment methods")

    if unverified_ratio >= 0.5:
        parts.append(f"{unverified_ratio:.0%} of methods unverified")

    if newest_age <= 1:
        parts.append("Brand-new payment method added")
    elif newest_age <= 7:
        parts.append(f"Newest method added {newest_age:.0f} days ago")

    if not parts:
        return "Stable payment methods with no failures"

    return "; ".join(parts)
