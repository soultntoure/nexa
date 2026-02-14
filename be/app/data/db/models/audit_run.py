"""
AuditRun model — tracks background audit pipeline executions.

Columns:
- id: UUID (PK)
- run_id: str (unique, human-readable run identifier)
- status: str (pending/running/completed/failed/cancelled)
- run_mode: str (full/incremental)
- config_snapshot: JSONB (frozen config at run start)
- counters: JSONB (units_extracted, clusters_found, candidates_generated)
- timings: JSONB (phase durations in seconds)
- started_at, completed_at: datetime
- error_message: str (nullable, on failure)
- last_heartbeat_at: datetime (stale detection)
- idempotency_key: str (unique, prevents duplicate runs)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditRun(Base):
    __tablename__ = "audit_runs"
    __table_args__ = (
        Index("ix_audit_runs_run_id", "run_id", unique=True),
        Index("ix_audit_runs_idempotency", "idempotency_key", unique=True),
        Index("ix_audit_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    run_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="full")
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    counters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    timings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True,
    )
