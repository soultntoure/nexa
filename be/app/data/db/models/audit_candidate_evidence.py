"""
AuditCandidateEvidence model — links candidates to supporting text units.

Each row connects a candidate pattern to a specific text unit with
evidence type, rank, and snippet for display.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


class AuditCandidateEvidence(Base):
    __tablename__ = "audit_candidate_evidence"
    __table_args__ = (
        Index("ix_audit_evidence_candidate_id", "candidate_id"),
        Index("ix_audit_evidence_unit_id", "unit_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("audit_candidates.candidate_id"),
        nullable=False,
    )
    unit_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="supporting",
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True,
    )

    candidate: Mapped[AuditCandidate] = relationship(back_populates="evidence")


from app.data.db.models.audit_candidate import AuditCandidate  # noqa: E402
