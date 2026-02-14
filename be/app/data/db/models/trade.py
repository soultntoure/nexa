"""
Trade model — trading activity records.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- instrument: str (forex pair, stock, crypto pair)
- trade_type: str (buy/sell)
- amount: Decimal
- pnl: Decimal (profit/loss)
- opened_at: datetime
- closed_at: datetime (nullable if open)
- created_at: datetime

Index: (customer_id, opened_at)
Used by trading_behavior indicator to assess activity level.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_customer_opened", "customer_id", "opened_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    instrument: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False
    )
    pnl: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    customer: Mapped[Customer] = relationship(back_populates="trades")
