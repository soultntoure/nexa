"""
IPHistory model — IP address usage records.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- ip_address: str
- location: str (city/country derived)
- is_vpn: bool
- first_seen_at: datetime
- last_seen_at: datetime
- created_at: datetime

Index: (customer_id, last_seen_at), (ip_address)
Used by geographic indicator for travel/VPN analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IPHistory(Base):
    __tablename__ = "ip_history"
    __table_args__ = (
        Index("ix_ip_history_customer_last_seen", "customer_id", "last_seen_at"),
        Index("ix_ip_history_ip_address", "ip_address"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_vpn: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    customer: Mapped[Customer] = relationship(back_populates="ip_history")
