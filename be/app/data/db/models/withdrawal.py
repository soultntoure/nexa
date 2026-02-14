"""
Withdrawal model — withdrawal request records.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- amount: Decimal
- currency: str
- payment_method_id: UUID (FK -> payment_methods)
- recipient_name: str
- recipient_account: str
- ip_address: str
- device_fingerprint: str
- location: str
- status: str (pending/approved/escalated/blocked)
- is_fraud: bool (nullable — admin ground-truth label)
- fraud_notes: str (nullable — admin explanation)
- requested_at: datetime
- processed_at: datetime (nullable)
- created_at: datetime

Relationships: decision (1:1), indicator_results (1:many)
Index: (customer_id, requested_at)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        Index(
            "ix_withdrawals_customer_requested",
            "customer_id",
            "requested_at",
        ),
        Index("ix_withdrawals_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payment_method_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payment_methods.id"), nullable=False
    )
    recipient_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    recipient_account: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    device_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    location: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    is_fraud: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=None
    )
    fraud_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    customer: Mapped[Customer] = relationship(back_populates="withdrawals")
    payment_method: Mapped[PaymentMethod] = relationship(
        back_populates="withdrawals"
    )
    decision: Mapped[WithdrawalDecision | None] = relationship(
        back_populates="withdrawal", uselist=False
    )
    indicator_results: Mapped[list[IndicatorResult]] = relationship(
        back_populates="withdrawal"
    )
    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="withdrawal")
    alerts: Mapped[list[Alert]] = relationship(back_populates="withdrawal")
    feedback: Mapped[list[Feedback]] = relationship(
        back_populates="withdrawal"
    )
