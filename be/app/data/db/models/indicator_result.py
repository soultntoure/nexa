"""
IndicatorResult model — per-indicator score for a withdrawal.

Columns:
- id: UUID (PK)
- withdrawal_id: UUID (FK -> withdrawals)
- indicator_name: str
- score: float (0.0-1.0)
- weight: float
- confidence: float
- reasoning: text
- evidence: JSON
- created_at: datetime

Many-to-one with Withdrawal. One row per indicator per withdrawal.
Index: (withdrawal_id, indicator_name)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IndicatorResult(Base):
    __tablename__ = "indicator_results"
    __table_args__ = (
        Index(
            "ix_indicator_results_withdrawal_name",
            "withdrawal_id",
            "indicator_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("withdrawals.id"), nullable=False
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluations.id"), nullable=True,
    )
    indicator_name: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──
    withdrawal: Mapped[Withdrawal] = relationship(
        back_populates="indicator_results"
    )
    evaluation: Mapped[Evaluation | None] = relationship(
        back_populates="indicator_results",
    )
