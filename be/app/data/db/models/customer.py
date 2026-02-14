"""
Customer model.

Columns:
- id: UUID (PK)
- external_id: str (unique, the customer_id used in API)
- name: str
- email: str
- country: str
- registration_date: datetime
- is_flagged: bool (benchmark flag for testing)
- created_at, updated_at: datetime

Relationships: transactions, withdrawals, devices, payment_methods
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False
    )
    country: Mapped[str] = mapped_column(String(3), nullable=False)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    is_flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # ── Relationships ──
    payment_methods: Mapped[list[PaymentMethod]] = relationship(
        back_populates="customer"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="customer"
    )
    trades: Mapped[list[Trade]] = relationship(back_populates="customer")
    withdrawals: Mapped[list[Withdrawal]] = relationship(
        back_populates="customer"
    )
    devices: Mapped[list[Device]] = relationship(back_populates="customer")
    ip_history: Mapped[list[IPHistory]] = relationship(
        back_populates="customer"
    )
    alerts: Mapped[list[Alert]] = relationship(back_populates="customer")
