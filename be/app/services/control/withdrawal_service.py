"""Withdrawal lifecycle helpers — create records, update status."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data.db.models.customer import Customer
from app.data.db.models.payment_method import PaymentMethod
from app.data.db.models.withdrawal import Withdrawal

logger = logging.getLogger(__name__)


async def ensure_withdrawal_exists(
    session_factory: async_sessionmaker[AsyncSession],
    withdrawal_id: uuid.UUID,
    customer_id: str,
    amount: float,
    recipient_name: str | None,
    recipient_account: str | None,
    ip_address: str | None,
    device_fingerprint: str | None,
) -> None:
    """Create a withdrawal record if it doesn't already exist."""
    async with session_factory() as session:
        existing = await session.get(Withdrawal, withdrawal_id)
        if existing:
            return

        result = await session.execute(
            select(Customer).where(Customer.external_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        pm_result = await session.execute(
            select(PaymentMethod)
            .where(PaymentMethod.customer_id == customer.id)
            .limit(1)
        )
        pm = pm_result.scalar_one_or_none()
        if not pm:
            raise ValueError(f"No payment method for customer {customer_id}")

        withdrawal = Withdrawal(
            id=withdrawal_id,
            customer_id=customer.id,
            amount=amount,
            currency="USD",
            payment_method_id=pm.id,
            recipient_name=recipient_name,
            recipient_account=recipient_account,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
            status="pending",
            requested_at=datetime.now(timezone.utc),
        )
        session.add(withdrawal)
        await session.commit()


async def update_withdrawal_status(
    session_factory: async_sessionmaker[AsyncSession],
    withdrawal_id: uuid.UUID,
    status: str,
) -> None:
    """Update withdrawal status after evaluation or officer decision."""
    async with session_factory() as session:
        withdrawal = await session.get(Withdrawal, withdrawal_id)
        if withdrawal:
            withdrawal.status = status
            withdrawal.processed_at = datetime.now(timezone.utc)
            await session.commit()
