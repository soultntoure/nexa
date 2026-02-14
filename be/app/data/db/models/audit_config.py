"""
AuditConfig model — background audit pipeline configuration.

Columns:
- id: UUID (PK)
- lookback_days: int (default 7)
- max_candidates: int (default 50)
- output_dir: str (default "outputs/background_audits/stage_1")
- min_events: int (default 5) — quality gate
- min_accounts: int (default 2) — quality gate
- min_confidence: float (default 0.50) — quality gate
- updated_by: str (admin_id or "system")
- reason: text (why updated)
- is_active: bool (only one active at a time)
- created_at: datetime

Soft versioning: new row per change, is_active=True for current config.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditConfig(Base):
    __tablename__ = "audit_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    lookback_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7
    )
    max_candidates: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50
    )
    output_dir: Mapped[str] = mapped_column(
        String(255), nullable=False, default="outputs/background_audits/stage_1"
    )
    min_events: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    min_accounts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )
    min_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.50
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
