"""
Alert model — persisted alerts for escalated/blocked decisions.

Columns:
- id: UUID (PK)
- withdrawal_id: UUID (FK -> withdrawals)
- customer_id: UUID (FK -> customers)
- alert_type: str (escalation/block)
- risk_score: float
- top_indicators: JSON (list of indicator names)
- is_read: bool (default False)
- created_at: datetime

Index: (created_at DESC), (is_read)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_is_read", "is_read"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("withdrawals.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    top_indicators: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    withdrawal: Mapped[Withdrawal] = relationship(
        back_populates="alerts"
    )
    customer: Mapped[Customer] = relationship(back_populates="alerts")
