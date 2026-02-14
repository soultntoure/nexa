"""
Customer list endpoint — reads from the customers table.

GET /api/customers — List all customers (external_id, name, country)
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.engine import get_session
from app.data.db.models.customer import Customer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
async def list_customers(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return all customers with their external_id, name, and country."""
    try:
        stmt = select(
            Customer.external_id,
            Customer.name,
            Customer.email,
            Customer.country,
            Customer.registration_date,
            Customer.is_flagged,
            Customer.flag_reason,
        ).order_by(Customer.external_id)

        rows = (await session.execute(stmt)).all()

        return [
            {
                "id": row.external_id,
                "name": row.name,
                "email": row.email,
                "country": row.country,
                "registration_date": row.registration_date.isoformat() if row.registration_date else None,
                "is_flagged": row.is_flagged,
                "flag_reason": row.flag_reason,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.exception("list_customers error: %s", exc)
        return []
