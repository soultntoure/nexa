"""
PatternMatch model — links a FraudPattern to a matched customer.

Each row represents one customer's membership in a detected fraud pattern.
The is_current flag allows soft-invalidation when patterns are re-scanned.

Columns:
- id: UUID (PK)
- pattern_id: FK -> fraud_patterns (CASCADE delete)
- customer_id: FK -> customers
- confidence: float (0-1 match strength)
- evidence: JSONB (what specifically matched)
- detected_at: datetime
- is_current: bool (soft-invalidation flag)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatternMatch(Base):
    __tablename__ = "pattern_matches"
    __table_args__ = (
        Index(
            "ix_pm_customer_current", "customer_id",
            postgresql_where=text("is_current = TRUE"),
        ),
        Index(
            "ix_pm_pattern_current", "pattern_id",
            postgresql_where=text("is_current = TRUE"),
        ),
        Index(
            "ix_pm_unique_current", "pattern_id", "customer_id",
            unique=True, postgresql_where=text("is_current = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pattern_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fraud_patterns.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    pattern: Mapped["FraudPattern"] = relationship(back_populates="matches")
    customer: Mapped["Customer"] = relationship()
