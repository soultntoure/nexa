"""
FraudPattern model — Phase 2 cross-customer fraud pattern entity.

Represents a discovered fraud pattern (e.g. shared device ring,
no-trade withdrawal cluster) with lifecycle management:
CANDIDATE -> ACTIVE -> DISABLED.

Columns:
- id: UUID (PK)
- pattern_type: str (e.g. 'no_trade_withdrawal', 'shared_device_ring')
- description: text
- definition: JSONB (technical criteria for matching)
- evidence: JSONB (supporting evidence and statistics)
- state: str ('candidate' | 'active' | 'disabled')
- confidence: float (0-1)
- frequency: int (times pattern has matched)
- precision_score: float (historical TP / (TP + FP)), nullable
- detected_at, activated_at, disabled_at, last_matched_at: datetime
- activated_by, disabled_by: UUID
- disabled_reason: text
- created_at: datetime
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FraudPattern(Base):
    __tablename__ = "fraud_patterns"
    __table_args__ = (
        Index("ix_patterns_state", "state"),
        Index("ix_patterns_type_state", "pattern_type", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    precision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    disabled_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    disabled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Relationships
    matches: Mapped[list["PatternMatch"]] = relationship(
        back_populates="pattern", cascade="all, delete-orphan"
    )
