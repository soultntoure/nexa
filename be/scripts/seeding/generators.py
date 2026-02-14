"""Bulk data generators for seed customers."""

import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.data.db.models import Trade, Transaction, Withdrawal

from .constants import INSTRUMENTS


def _gen_trades(
    customer_id: uuid.UUID,
    n: int,
    start: datetime,
    end: datetime,
    amount_lo: float,
    amount_hi: float,
) -> list[Trade]:
    """Generate n closed trades spread between start and end."""
    trades = []
    span = max((end - start).total_seconds(), 1)
    for i in range(n):
        opened = start + timedelta(
            seconds=span * i / n + random.uniform(0, span / n * 0.3)
        )
        duration = random.randint(300, 14400)
        closed = opened + timedelta(seconds=duration)
        amount = Decimal(str(round(random.uniform(amount_lo, amount_hi), 2)))
        pnl = Decimal(str(round(random.uniform(-80, 120), 2)))
        trades.append(
            Trade(
                id=uuid.uuid4(),
                customer_id=customer_id,
                instrument=random.choice(INSTRUMENTS),
                trade_type=random.choice(["buy", "sell"]),
                amount=amount,
                pnl=pnl,
                opened_at=opened,
                closed_at=closed,
                created_at=opened,
            )
        )
    return trades


def _gen_deposits(
    customer_id: uuid.UUID,
    pm_id: uuid.UUID,
    n: int,
    start: datetime,
    end: datetime,
    amount_lo: float,
    amount_hi: float,
    ip: str,
    currency: str = "USD",
) -> list[Transaction]:
    """Generate n successful deposit transactions."""
    txns = []
    span = max((end - start).total_seconds(), 1)
    for i in range(n):
        ts = start + timedelta(
            seconds=span * i / n + random.uniform(0, span / n * 0.6)
        )
        amount = Decimal(str(round(random.uniform(amount_lo, amount_hi), 2)))
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                customer_id=customer_id,
                type="deposit",
                amount=amount,
                currency=currency,
                status="success",
                payment_method_id=pm_id,
                ip_address=ip,
                timestamp=ts,
                created_at=ts,
            )
        )
    return txns


def _gen_past_withdrawals(
    customer_id: uuid.UUID,
    pm_id: uuid.UUID,
    n: int,
    start: datetime,
    end: datetime,
    amount_lo: float,
    amount_hi: float,
    ip: str,
    fingerprint: str,
    recipient_name: str,
    recipient_account: str,
    location: str,
    currency: str = "USD",
) -> list[Withdrawal]:
    """Generate n past approved withdrawals."""
    wds = []
    span = max((end - start).total_seconds(), 1)
    for i in range(n):
        ts = start + timedelta(
            seconds=span * i / n + random.uniform(0, span / n * 0.6)
        )
        amount = Decimal(str(round(random.uniform(amount_lo, amount_hi), 2)))
        wds.append(
            Withdrawal(
                id=uuid.uuid4(),
                customer_id=customer_id,
                amount=amount,
                currency=currency,
                payment_method_id=pm_id,
                recipient_name=recipient_name,
                recipient_account=recipient_account,
                ip_address=ip,
                device_fingerprint=fingerprint,
                location=location,
                status="approved",
                is_fraud=False,
                requested_at=ts,
                processed_at=ts + timedelta(seconds=3),
                created_at=ts,
            )
        )
    return wds
