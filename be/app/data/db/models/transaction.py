"""
Transaction model — deposits and general account activity.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- type: str (deposit/withdrawal/trade_pnl)
- amount: Decimal
- currency: str
- status: str (success/failed/pending)
- payment_method_id: UUID (FK, nullable)
- error_code: str (nullable, for failed transactions)
- ip_address: str
- timestamp: datetime
- created_at: datetime

Index: (customer_id, timestamp), (customer_id, type)
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


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_customer_ts", "customer_id", "timestamp"),
        Index("ix_transactions_customer_type", "customer_id", "type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(15), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_methods.id"), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    customer: Mapped[Customer] = relationship(back_populates="transactions")
    payment_method: Mapped[PaymentMethod | None] = relationship(
        back_populates="transactions"
    )
