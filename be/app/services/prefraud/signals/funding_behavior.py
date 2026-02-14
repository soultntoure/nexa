"""
Funding Behavior signal — detects deposit-and-run patterns and funding imbalance.

Sub-signals:
- Deposit-to-trade ratio (amount): <= 2.0 safe, >= 20.0 risky
- Deposit-to-withdrawal ratio (amount): >= 3.0 safe, <= 1.1 risky
- Has zero trades: no safe, yes (with deposits > 0) risky

Edge case: Account with zero deposits and zero trades scores 0.0.

Inputs: transactions, trades, withdrawals
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.signals.base import BaseSignal, SignalResult, _linear_score


class FundingBehaviorSignal(BaseSignal):
    """Scores deposit/trade/withdrawal imbalance and deposit-and-run patterns."""

    name = "funding_behavior"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        data = await _fetch_funding_data(customer_id, session)
        score, evidence, reason = _compute_score(data)
        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )


async def _fetch_funding_data(
    customer_id: uuid.UUID, session: AsyncSession,
) -> dict:
    """Fetch deposit, trade, and withdrawal totals."""
    result = await session.execute(
        text("""
            SELECT
                COALESCE(SUM(t.amount) FILTER (
                    WHERE t.type = 'deposit'
                ), 0) AS total_deposits,
                COALESCE(SUM(t.amount) FILTER (
                    WHERE t.type = 'withdrawal'
                ), 0) AS total_withdrawals_tx
            FROM transactions t
            WHERE t.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    tx_row = result.mappings().first() or {}

    trade_result = await session.execute(
        text("""
            SELECT
                COALESCE(SUM(ABS(tr.amount)), 0) AS total_trade_volume,
                COUNT(tr.id) AS trade_count
            FROM trades tr
            WHERE tr.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    tr_row = trade_result.mappings().first() or {}

    wd_result = await session.execute(
        text("""
            SELECT COALESCE(SUM(w.amount), 0) AS total_withdrawals
            FROM withdrawals w
            WHERE w.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    wd_row = wd_result.mappings().first() or {}

    return {
        "total_deposits": float(tx_row.get("total_deposits", 0)),
        "total_withdrawals": float(wd_row.get("total_withdrawals", 0)),
        "total_trade_volume": float(tr_row.get("total_trade_volume", 0)),
        "trade_count": int(tr_row.get("trade_count", 0)),
    }


def _compute_score(data: dict) -> tuple[float, dict, str]:
    """Score funding behavior from sub-signals."""
    deposits = data["total_deposits"]
    withdrawals = data["total_withdrawals"]
    trade_vol = data["total_trade_volume"]
    trade_count = data["trade_count"]

    # Edge case: no funding activity at all
    if deposits == 0 and trade_count == 0:
        evidence = {
            "total_deposits": deposits,
            "total_withdrawals": withdrawals,
            "total_trade_volume": trade_vol,
            "deposit_to_trade_ratio": 0.0,
            "deposit_to_withdrawal_ratio": 0.0,
            "has_zero_trades": True,
        }
        return 0.0, evidence, "No funding activity to evaluate"

    # Sub-signal 1: deposit-to-trade ratio
    if trade_vol > 0:
        dep_trade_ratio = deposits / trade_vol
        dep_trade_score = _linear_score(dep_trade_ratio, 2.0, 20.0)
    elif deposits > 0:
        # Deposits but zero trading — maximum risk for this sub-signal
        dep_trade_ratio = float("inf")
        dep_trade_score = 1.0
    else:
        dep_trade_ratio = 0.0
        dep_trade_score = 0.0

    # Sub-signal 2: deposit-to-withdrawal ratio (inverted — low is risky)
    if withdrawals > 0:
        dep_wd_ratio = deposits / withdrawals
        dep_wd_score = _linear_score(dep_wd_ratio, 3.0, 1.1)
    else:
        dep_wd_ratio = float("inf") if deposits > 0 else 0.0
        dep_wd_score = 0.0  # No withdrawals = not risky for this sub-signal

    # Sub-signal 3: has zero trades with deposits
    has_zero_trades = trade_count == 0 and deposits > 0
    zero_trades_score = 1.0 if has_zero_trades else 0.0

    # Weighted average
    score = round(
        (dep_trade_score * 0.4
         + dep_wd_score * 0.3
         + zero_trades_score * 0.3),
        4,
    )

    evidence = {
        "total_deposits": round(deposits, 2),
        "total_withdrawals": round(withdrawals, 2),
        "total_trade_volume": round(trade_vol, 2),
        "deposit_to_trade_ratio": (
            round(dep_trade_ratio, 2) if dep_trade_ratio != float("inf") else None
        ),
        "deposit_to_withdrawal_ratio": (
            round(dep_wd_ratio, 2) if dep_wd_ratio != float("inf") else None
        ),
        "has_zero_trades": has_zero_trades,
    }

    reason = _build_reason(dep_trade_ratio, dep_wd_ratio, has_zero_trades, deposits)

    return score, evidence, reason


def _build_reason(
    dep_trade_ratio: float,
    dep_wd_ratio: float,
    has_zero_trades: bool,
    deposits: float,
) -> str:
    """Build plain-English explanation."""
    parts: list[str] = []

    if has_zero_trades and deposits > 0:
        parts.append(
            f"${deposits:,.0f} deposited with zero trading — deposit & run signal"
        )
    elif dep_trade_ratio >= 20:
        parts.append(
            f"Deposit-to-trade ratio extremely high ({dep_trade_ratio:.0f}:1)"
        )
    elif dep_trade_ratio >= 5:
        parts.append(f"Deposit-to-trade ratio elevated ({dep_trade_ratio:.1f}:1)")

    if dep_wd_ratio != float("inf") and dep_wd_ratio <= 1.5:
        parts.append("Withdrawing nearly everything deposited")
    elif dep_wd_ratio != float("inf") and dep_wd_ratio <= 2.0:
        parts.append("High withdrawal-to-deposit ratio")

    if not parts:
        return "Balanced funding and trading activity"

    return "; ".join(parts)
