"""Service to gather investigation evidence for a withdrawal's customer."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.fraud.investigate import (
    CustomerSummary,
    DeviceRecord,
    InvestigateResponse,
    IPRecord,
    RecentWithdrawal,
)
from app.data.db.models.customer import Customer
from app.data.db.models.device import Device
from app.data.db.models.ip_history import IPHistory
from app.data.db.models.withdrawal import Withdrawal


async def get_investigation_evidence(
    session: AsyncSession,
    withdrawal_id: uuid.UUID,
) -> InvestigateResponse:
    """Fetch customer evidence for a given withdrawal."""
    customer_id = await _get_customer_id(session, withdrawal_id)
    customer = await _get_customer(session, customer_id)
    withdrawals = await _get_recent_withdrawals(session, customer_id)
    ips = await _get_ip_history(session, customer_id)
    devices = await _get_devices(session, customer_id)

    return InvestigateResponse(
        customer=customer,
        recent_withdrawals=withdrawals,
        ip_history=ips,
        devices=devices,
    )


async def _get_customer_id(
    session: AsyncSession, withdrawal_id: uuid.UUID,
) -> uuid.UUID:
    result = await session.execute(
        select(Withdrawal.customer_id)
        .where(Withdrawal.id == withdrawal_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"Withdrawal {withdrawal_id} not found")
    return row


async def _get_customer(
    session: AsyncSession, customer_id: uuid.UUID,
) -> CustomerSummary:
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    c = result.scalar_one()
    return CustomerSummary(
        name=c.name,
        external_id=c.external_id,
        country=c.country,
        registration_date=c.registration_date,
        is_flagged=c.is_flagged,
    )


async def _get_recent_withdrawals(
    session: AsyncSession, customer_id: uuid.UUID,
) -> list[RecentWithdrawal]:
    result = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.customer_id == customer_id)
        .order_by(Withdrawal.requested_at.desc())
        .limit(5)
    )
    return [
        RecentWithdrawal(
            amount=w.amount,
            currency=w.currency,
            status=w.status,
            recipient_name=w.recipient_name,
            requested_at=w.requested_at,
        )
        for w in result.scalars()
    ]


async def _get_ip_history(
    session: AsyncSession, customer_id: uuid.UUID,
) -> list[IPRecord]:
    result = await session.execute(
        select(IPHistory)
        .where(IPHistory.customer_id == customer_id)
        .order_by(IPHistory.last_seen_at.desc())
        .limit(10)
    )
    return [
        IPRecord(
            ip_address=ip.ip_address,
            location=ip.location,
            is_vpn=ip.is_vpn,
            last_seen_at=ip.last_seen_at,
        )
        for ip in result.scalars()
    ]


async def _get_devices(
    session: AsyncSession, customer_id: uuid.UUID,
) -> list[DeviceRecord]:
    result = await session.execute(
        select(Device)
        .where(Device.customer_id == customer_id)
        .order_by(Device.last_seen_at.desc())
        .limit(10)
    )
    return [
        DeviceRecord(
            fingerprint=d.fingerprint,
            os=d.os,
            browser=d.browser,
            is_trusted=d.is_trusted,
            last_seen_at=d.last_seen_at,
        )
        for d in result.scalars()
    ]
