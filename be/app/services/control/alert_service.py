"""Alert service — list alerts, compute fraud patterns, bulk actions."""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.data.db.models.alert import Alert
from app.data.db.models.customer import Customer
from app.data.db.models.evaluation import Evaluation
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.models.withdrawal import Withdrawal

logger = logging.getLogger(__name__)


async def create_fraud_alert(
    session_factory,
    customer_id: str,
    withdrawal_id: uuid.UUID,
    risk_score: float,
    decision: str,
    indicator_names: list[str],
) -> None:
    """Auto-create an alert when evaluation results in escalation/block."""
    async with session_factory() as session:
        result = await session.execute(
            select(Customer).where(Customer.external_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            return

        alert = Alert(
            withdrawal_id=withdrawal_id,
            customer_id=customer.id,
            alert_type="block" if decision == "blocked" else "escalation",
            risk_score=risk_score,
            top_indicators=indicator_names,
        )
        session.add(alert)
        await session.commit()


async def list_alerts(
    session: AsyncSession,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    """Fetch recent alerts with customer/withdrawal data + fraud patterns."""
    stmt = (
        select(Alert)
        .options(joinedload(Alert.customer), joinedload(Alert.withdrawal))
        .order_by(desc(Alert.created_at))
        .limit(50)
    )
    if since:
        stmt = stmt.where(Alert.created_at >= since)
    if until:
        stmt = stmt.where(Alert.created_at <= until)
    rows = (await session.execute(stmt)).scalars().unique().all()

    alerts = []
    for a in rows:
        indicator_details = await _get_indicator_details(session, a)
        alerts.append(_format_alert(a, indicator_details))

    patterns = await compute_fraud_patterns(session)
    total = (await session.execute(
        select(func.count()).select_from(Alert)
    )).scalar_one()

    return {"alerts": alerts, "total": total, "patterns": patterns}


async def _get_indicator_details(
    session: AsyncSession, alert: Alert,
) -> list[dict]:
    """Get top indicator scores for an alert's withdrawal."""
    w = alert.withdrawal
    if not w:
        return _fallback_indicators(alert)

    ev_stmt = (
        select(Evaluation)
        .where(Evaluation.withdrawal_id == w.id)
        .order_by(desc(Evaluation.checked_at))
        .limit(1)
    )
    ev = (await session.execute(ev_stmt)).scalar_one_or_none()
    if not ev:
        return _fallback_indicators(alert)

    ind_stmt = (
        select(IndicatorResult)
        .where(IndicatorResult.evaluation_id == ev.id)
        .order_by(desc(IndicatorResult.score))
        .limit(3)
    )
    ind_rows = (await session.execute(ind_stmt)).scalars().all()
    if not ind_rows:
        return _fallback_indicators(alert)

    return [
        {"name": ind.indicator_name, "score": round(ind.score * 100)}
        for ind in ind_rows
    ]


def _fallback_indicators(alert: Alert) -> list[dict]:
    """Use stored top_indicators when DB indicator data is unavailable."""
    if not alert.top_indicators:
        return []
    return [
        {"name": name, "score": round(alert.risk_score * 100)}
        for name in alert.top_indicators[:3]
    ]


def _format_alert(alert: Alert, indicator_details: list[dict]) -> dict:
    """Format a single alert for API response."""
    c = alert.customer
    w = alert.withdrawal
    return {
        "id": str(alert.id),
        "type": alert.alert_type,
        "customer_name": c.name if c else "Unknown",
        "account_id": c.external_id if c else "",
        "risk_score": round(alert.risk_score * 100),
        "indicators": indicator_details,
        "timestamp": alert.created_at.isoformat(),
        "read": alert.is_read,
        "amount": float(w.amount) if w else 0,
        "currency": w.currency if w else "USD",
    }


async def compute_fraud_patterns(session: AsyncSession) -> list[dict]:
    """Compute fraud pattern stats from real indicator data."""
    pattern_defs = [
        ("No Trade Pattern", "no_trade", "trading_behavior", 0.7, 94),
        ("Velocity Abuse", "velocity", "velocity", 0.6, 78),
        ("Card Testing", "card_testing", "card_errors", 0.5, 91),
        ("Geographic Anomaly", "geographic", "geographic", 0.6, 87),
    ]
    patterns = []
    for name, key, indicator, threshold, confidence in pattern_defs:
        row = await _query_pattern_stats(session, indicator, threshold)
        patterns.append({
            "name": name,
            "key": key,
            "accounts_affected": row[0],
            "total_exposure": round(float(row[1])),
            "confidence": confidence,
        })
    return patterns


async def _query_pattern_stats(
    session: AsyncSession, indicator_name: str, threshold: float,
) -> tuple[int, float]:
    """Count distinct withdrawals and sum amounts for a flagged indicator."""
    result = (await session.execute(
        select(
            func.count(func.distinct(IndicatorResult.withdrawal_id)),
            func.coalesce(
                func.sum(Withdrawal.amount).filter(
                    IndicatorResult.score >= threshold
                ),
                0,
            ),
        )
        .join(Withdrawal, IndicatorResult.withdrawal_id == Withdrawal.id)
        .where(
            IndicatorResult.indicator_name == indicator_name,
            IndicatorResult.score >= threshold,
        )
    )).one()
    return result


async def execute_bulk_action(
    session: AsyncSession,
    alert_ids: list[str],
    action: str,
) -> dict:
    """Process bulk actions on alerts — updates DB."""
    alert_uuids = _parse_uuids(alert_ids)
    if not alert_uuids:
        return _bulk_result(action, alert_ids, 0, "no_valid_ids")

    if action == "dismiss":
        await _dismiss_alerts(session, alert_uuids)
        affected = len(alert_uuids)
    elif action in ("lock_accounts", "freeze_withdrawals"):
        affected = await _lock_or_freeze(session, alert_uuids, action)
    else:
        affected = 0

    await session.commit()
    return _bulk_result(action, alert_ids, affected, "completed")


def _parse_uuids(ids: list[str]) -> list[uuid.UUID]:
    """Parse string IDs to UUIDs, skipping invalid ones."""
    result = []
    for aid in ids:
        try:
            result.append(uuid.UUID(aid))
        except ValueError:
            continue
    return result


async def _dismiss_alerts(
    session: AsyncSession, alert_uuids: list[uuid.UUID],
) -> None:
    """Mark alerts as read."""
    await session.execute(
        update(Alert).where(Alert.id.in_(alert_uuids)).values(is_read=True)
    )


async def _lock_or_freeze(
    session: AsyncSession,
    alert_uuids: list[uuid.UUID],
    action: str,
) -> int:
    """Flag customers and block pending withdrawals for given alerts."""
    alert_rows = (await session.execute(
        select(Alert).where(Alert.id.in_(alert_uuids))
    )).scalars().all()

    customer_ids = list({a.customer_id for a in alert_rows})
    if customer_ids:
        await session.execute(
            update(Customer)
            .where(Customer.id.in_(customer_ids))
            .values(is_flagged=True, flag_reason=f"Bulk action: {action}")
        )

    withdrawal_ids = [a.withdrawal_id for a in alert_rows]
    if withdrawal_ids:
        await session.execute(
            update(Withdrawal)
            .where(
                Withdrawal.id.in_(withdrawal_ids),
                Withdrawal.status.in_(["pending", "escalated"]),
            )
            .values(status="blocked")
        )

    await _dismiss_alerts(session, alert_uuids)
    return len(alert_rows)


def _bulk_result(
    action: str, alert_ids: list[str], affected: int, status: str,
) -> dict:
    return {
        "action": action,
        "affected_alert_ids": alert_ids,
        "affected_count": affected,
        "status": status,
    }
