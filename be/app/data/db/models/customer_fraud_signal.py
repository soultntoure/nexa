"""
CustomerFraudSignal model — per-customer feedback loop signal records.

Renamed from FraudPattern (Phase 1) to free the name for the Phase 2
cross-customer pattern entity.

Columns:
- id: UUID (PK)
- pattern_type: str
- description: text
- indicator_combination: JSON (list of indicator names)
- frequency: int (times observed)
- confidence: float
- vector_id: str (reference to ChromaDB embedding)
- detected_at: datetime
- created_at: datetime
- customer_id: FK -> customers
- evaluation_id: FK -> evaluations
- signal_type: str
- indicator_scores: JSONB
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomerFraudSignal(Base):
    __tablename__ = "customer_fraud_signals"
    __table_args__ = (
        Index("ix_cfs_customer_signal", "customer_id", "signal_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    indicator_combination: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    frequency: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    vector_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Feedback loop columns (Phase 1)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluations.id"), nullable=True
    )
    signal_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    indicator_scores: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
