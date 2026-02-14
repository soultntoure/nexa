"""
Device model — device fingerprint records.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- fingerprint: str (device hash)
- os: str
- browser: str
- screen_resolution: str
- first_seen_at: datetime
- last_seen_at: datetime
- is_trusted: bool
- created_at: datetime

Index: (fingerprint) for cross-account lookups, (customer_id)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_fingerprint", "fingerprint"),
        Index("ix_devices_customer_id", "customer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    os: Mapped[str | None] = mapped_column(String(30), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(50), nullable=True)
    screen_resolution: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    is_trusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    customer: Mapped[Customer] = relationship(back_populates="devices")
