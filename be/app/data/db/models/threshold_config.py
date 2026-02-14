"""
ThresholdConfig model — scoring boundaries and weights.

Columns:
- id: UUID (PK)
- approve_below: float (default 30.0)
- escalate_below: float (default 70.0)
- indicator_weights: JSON (dict of indicator_name -> weight)
- updated_by: str (admin_id or "system")
- reason: text (why updated)
- is_active: bool (only one active at a time)
- created_at: datetime

Soft versioning: new row per change, is_active=True for current config.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ThresholdConfig(Base):
    __tablename__ = "threshold_config"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    approve_below: Mapped[float] = mapped_column(
        Float, nullable=False, default=30.0
    )
    escalate_below: Mapped[float] = mapped_column(
        Float, nullable=False, default=70.0
    )
    indicator_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    updated_by: Mapped[str] = mapped_column(
        String(50), nullable=False, default="system"
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
