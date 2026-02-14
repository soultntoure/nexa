"""
Feedback model — admin review of decisions.

Columns:
- id: UUID (PK)
- withdrawal_id: UUID (FK -> withdrawals)
- admin_id: str (simple identifier, no auth)
- is_correct: bool
- reason: text
- created_at: datetime

Index: (withdrawal_id), (created_at)
Used by feedback_service to track accuracy and adjust thresholds.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_withdrawal_id", "withdrawal_id"),
        Index("ix_feedback_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("withdrawals.id"), nullable=False
    )
    admin_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    withdrawal: Mapped[Withdrawal] = relationship(
        back_populates="feedback"
    )
    action_by_admin: Mapped[Admin | None] = relationship(
        back_populates="feedback_actions",
    )
