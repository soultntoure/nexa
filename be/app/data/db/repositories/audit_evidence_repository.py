"""Repository for audit_candidate_evidence table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence
from app.data.db.repositories.base_repository import BaseRepository


class AuditEvidenceRepository(BaseRepository[AuditCandidateEvidence]):
    model_class = AuditCandidateEvidence

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add_evidence_batch(
        self, evidence_list: list[AuditCandidateEvidence],
    ) -> None:
        for ev in evidence_list:
            self.session.add(ev)
        await self.session.commit()

    async def get_for_candidate(
        self, candidate_id: str,
    ) -> list[AuditCandidateEvidence]:
        stmt = (
            select(AuditCandidateEvidence)
            .where(AuditCandidateEvidence.candidate_id == candidate_id)
            .order_by(AuditCandidateEvidence.rank)
        )
        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())
        for e in entities:
            self._expunge(e)
        return entities
