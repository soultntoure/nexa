"""
PaymentMethod model.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- type: str (card/ewallet/bank_transfer/crypto)
- provider: str (visa, skrill, btc, etc.)
- last_four: str (nullable, masked card)
- is_verified: bool
- added_at: datetime
- last_used_at: datetime (nullable)
- is_blacklisted: bool (for risk scoring)
- created_at: datetime

Index: (customer_id, type)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    __table_args__ = (
        Index("ix_payment_methods_customer_type", "customer_id", "type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    last_four: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_blacklisted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    customer: Mapped[Customer] = relationship(back_populates="payment_methods")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="payment_method"
    )
    withdrawals: Mapped[list[Withdrawal]] = relationship(
        back_populates="payment_method"
    )
