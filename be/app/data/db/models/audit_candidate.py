"""
AuditCandidate model — discovered fraud pattern candidates for admin review.

Each candidate represents a cluster of similar reasoning from confirmed-fraud
cases. Includes quality scoring, novelty detection, and admin action tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditCandidate(Base):
    __tablename__ = "audit_candidates"
    __table_args__ = (
        Index("ix_audit_candidates_candidate_id", "candidate_id", unique=True),
        Index("ix_audit_candidates_run_id", "run_id"),
        Index("ix_audit_candidates_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True,
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cluster_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    novelty_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="new",
    )
    matched_cluster_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    support_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_accounts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pattern_card: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ignore_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suppressed_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    evidence: Mapped[list[AuditCandidateEvidence]] = relationship(
        back_populates="candidate",
    )


from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence  # noqa: E402
