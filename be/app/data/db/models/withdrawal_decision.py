"""
WithdrawalDecision model — stores the orchestrator's final decision.

Columns:
- id: UUID (PK)
- withdrawal_id: UUID (FK -> withdrawals, unique)
- decision: str (approve/escalate/block)
- composite_score: float (0-100)
- reasoning: text (full natural language explanation)
- decided_at: datetime
- created_at: datetime

One-to-one with Withdrawal.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WithdrawalDecision(Base):
    __tablename__ = "withdrawal_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("withdrawals.id"), unique=True, nullable=False
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluations.id"), nullable=True,
    )
    decision: Mapped[str] = mapped_column(String(15), nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    withdrawal: Mapped[Withdrawal] = relationship(
        back_populates="decision"
    )
