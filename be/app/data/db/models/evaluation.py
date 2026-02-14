"""
Evaluation model — one row per fraud-check pipeline run.

Columns:
- id: UUID (PK) — the evaluation_id threaded through the pipeline
- withdrawal_id: UUID (FK -> withdrawals)
- composite_score: float (0.0-1.0)
- decision: str (approved/escalated/blocked)
- risk_level: str (low/medium/high)
- summary: text
- has_hard_escalation: bool
- has_multi_critical: bool
- gray_zone_used: bool
- gray_zone_decision: str (nullable)
- gray_zone_reasoning: text (nullable)
- elapsed_s: float
- checked_at: datetime

One evaluation per pipeline invocation. One withdrawal may have multiple evaluations.
Index: (withdrawal_id, checked_at)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        Index("ix_evaluations_withdrawal_checked", "withdrawal_id", "checked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("withdrawals.id"), nullable=False,
    )
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(15), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    has_hard_escalation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_multi_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gray_zone_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gray_zone_decision: Mapped[str | None] = mapped_column(String(15), nullable=True)
    gray_zone_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    investigation_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    elapsed_s: Mapped[float] = mapped_column(Float, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    # ── Relationships ──
    withdrawal: Mapped[Withdrawal] = relationship(back_populates="evaluations")
    indicator_results: Mapped[list[IndicatorResult]] = relationship(
        back_populates="evaluation",
    )
