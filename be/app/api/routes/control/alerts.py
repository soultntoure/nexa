"""
Alert endpoints — queries REAL DB data.

GET  /api/alerts             — Get fraud alerts with patterns
POST /api/alerts/bulk-action — Lock accounts, freeze withdrawals, dismiss
POST /api/alerts/card-lockdown — Lock all accounts sharing a blocked card
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import update as sql_update

from app.data.db.engine import get_session
from app.data.db.models.alert import Alert
from app.services.control.alert_service import execute_bulk_action, list_alerts
from app.services.control.card_lockdown_service import (
    check_shared_card,
    execute_card_lockdown_by_customer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class BulkActionRequest(BaseModel):
    alert_ids: list[str]
    action: str
    admin_id: str | None = None


class CardLockdownRequest(BaseModel):
    customer_id: str
    risk_score: float = 0.85
    admin_id: str | None = None


@router.get("")
async def get_alerts(
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get recent fraud alerts from DB with computed patterns."""
    try:
        return await list_alerts(session, since=since, until=until)
    except Exception as exc:
        logger.exception("get_alerts error: %s", exc)
        return {"alerts": [], "total": 0, "patterns": []}


@router.post("/bulk-action")
async def bulk_action(
    request: BulkActionRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Process bulk actions on alerts — actually updates the DB."""
    try:
        return await execute_bulk_action(
            session, request.alert_ids, request.action,
            admin_id=request.admin_id,
        )
    except Exception as exc:
        logger.exception("bulk_action error: %s", exc)
        await session.rollback()
        return {
            "action": request.action,
            "affected_alert_ids": request.alert_ids,
            "affected_count": 0,
            "status": "error",
        }


class MarkReadRequest(BaseModel):
    alert_ids: list[str]


@router.patch("/read")
async def mark_alerts_read(
    request: MarkReadRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark specific alerts as read."""
    try:
        import uuid as _uuid
        uuids = [_uuid.UUID(aid) for aid in request.alert_ids]
        await session.execute(
            sql_update(Alert)
            .where(Alert.id.in_(uuids))
            .values(is_read=True)
        )
        await session.commit()
        return {"updated": len(uuids)}
    except Exception as exc:
        logger.exception("mark_alerts_read error: %s", exc)
        return {"updated": 0}


@router.get("/card-check/{external_id}")
async def card_check(
    external_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check if a customer has a card shared with other accounts."""
    try:
        return await check_shared_card(session, external_id)
    except Exception as exc:
        logger.exception("card_check error: %s", exc)
        return {"shared": False, "linked_count": 0}


@router.post("/card-lockdown")
async def card_lockdown(
    request: CardLockdownRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Lock all accounts sharing a card with the given customer."""
    try:
        return await execute_card_lockdown_by_customer(
            session, request.customer_id, request.risk_score,
            admin_id=request.admin_id,
        )
    except Exception as exc:
        logger.exception("card_lockdown error: %s", exc)
        await session.rollback()
        return _empty_lockdown_result(str(exc))


def _empty_lockdown_result(error: str = "") -> dict:
    result: dict = {
        "affected_customers": [],
        "affected_count": 0,
        "blacklisted_methods": 0,
    }
    if error:
        result["error"] = error
    return result
