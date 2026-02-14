"""
AuditTextUnit model — normalized text chunks from confirmed-fraud evaluations.

Each unit is a reasoning snippet extracted from investigation_data JSONB,
PII-masked and hashed for dedup. Linked to ChromaDB vectors via unit_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditTextUnit(Base):
    __tablename__ = "audit_text_units"
    __table_args__ = (
        Index("ix_audit_text_units_unit_id", "unit_id", unique=True),
        Index("ix_audit_text_units_text_hash", "text_hash"),
        Index("ix_audit_text_units_evaluation_id", "evaluation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id"), nullable=False,
    )
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("withdrawals.id"), nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    text_masked: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    embedding_model_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    vector_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
