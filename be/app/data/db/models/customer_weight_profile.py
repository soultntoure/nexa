"""
CustomerWeightProfile model — per-customer indicator weight overrides.

Columns:
- id: UUID (PK)
- customer_id: UUID (FK -> customers)
- indicator_weights: JSONB (per-indicator multipliers + metadata)
- blend_weights: JSONB (rule_engine/investigators split)
- decision_window: JSONB (rolling window of last 20 decisions)
- is_active: bool (only one active profile per customer)
- recalculated_at: datetime
- created_at: datetime

Index: (customer_id, is_active) for hot-path lookup.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomerWeightProfile(Base):
    __tablename__ = "customer_weight_profiles"
    __table_args__ = (
        Index(
            "ix_cwp_customer_active",
            "customer_id",
            "is_active",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    indicator_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    blend_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"rule_engine": 0.6, "investigators": 0.4},
    )
    decision_window: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    recalculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
