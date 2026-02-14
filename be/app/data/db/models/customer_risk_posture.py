"""
CustomerRiskPosture model — pre-fraud posture snapshots.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- posture: str ('normal' | 'watch' | 'high_risk')
- composite_score: float (0.0-1.0)
- signal_scores: JSONB (per-signal scores)
- signal_evidence: JSONB (top_reasons + per-signal evidence)
- trigger: str ('scheduled' | 'manual' | 'event:new_device' | ...)
- is_current: bool (only one per customer at a time)
- computed_at: datetime
- created_at: datetime

Every posture computation creates a new row with full snapshot.
Previous rows have is_current=FALSE for history/audit trail.

Index: (customer_id) WHERE is_current=TRUE for fast current lookup
Index: (customer_id, computed_at DESC) for history queries
Index: (posture) for aggregate reporting
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomerRiskPosture(Base):
    __tablename__ = "customer_risk_postures"
    __table_args__ = (
        Index(
            "ix_posture_customer_current",
            "customer_id",
            postgresql_where=text("is_current = TRUE"),
        ),
        Index(
            "ix_posture_customer_computed",
            "customer_id",
            "computed_at",
        ),
        Index("ix_posture_posture", "posture"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    posture: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    composite_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    signal_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    signal_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    trigger: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
