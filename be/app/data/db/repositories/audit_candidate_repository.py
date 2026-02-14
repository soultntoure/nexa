"""Repository for audit_candidates table."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.db.models.audit_candidate import AuditCandidate
from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence
from app.data.db.repositories.base_repository import BaseRepository


class AuditCandidateRepository(BaseRepository[AuditCandidate]):
    model_class = AuditCandidate

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_candidate(self, candidate: AuditCandidate) -> AuditCandidate:
        return await self.create(candidate)

    async def create_with_evidence(
        self,
        candidate: AuditCandidate,
        evidence_list: list[AuditCandidateEvidence],
    ) -> AuditCandidate:
        """Create candidate and evidence rows in one transaction."""
        return await self._save_with_evidence(candidate, evidence_list)

    async def update_with_evidence(
        self,
        candidate: AuditCandidate,
        evidence_list: list[AuditCandidateEvidence],
    ) -> AuditCandidate:
        """Update candidate and append evidence rows in one transaction."""
        return await self._save_with_evidence(candidate, evidence_list, merge_first=True)

    async def update_status(
        self, candidate_id: str, status: str,
    ) -> None:
        stmt = (
            update(AuditCandidate)
            .where(AuditCandidate.candidate_id == candidate_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def list_by_run(
        self, run_id: str, skip: int = 0, limit: int = 50,
    ) -> list[AuditCandidate]:
        stmt = (
            select(AuditCandidate)
            .options(selectinload(AuditCandidate.evidence))
            .where(AuditCandidate.run_id == run_id)
            .order_by(AuditCandidate.quality_score.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        entities = list(result.scalars().unique().all())
        for e in entities:
            self._expunge(e)
        return entities

    async def get_by_candidate_id(
        self, candidate_id: str,
    ) -> AuditCandidate | None:
        stmt = (
            select(AuditCandidate)
            .options(selectinload(AuditCandidate.evidence))
            .where(AuditCandidate.candidate_id == candidate_id)
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            self._expunge(entity)
        return entity

    async def increment_ignore_count(
        self, candidate_id: str,
    ) -> None:
        stmt = (
            update(AuditCandidate)
            .where(AuditCandidate.candidate_id == candidate_id)
            .values(
                ignore_count=AuditCandidate.ignore_count + 1,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def _save_with_evidence(
        self,
        candidate: AuditCandidate,
        evidence_list: list[AuditCandidateEvidence],
        merge_first: bool = False,
    ) -> AuditCandidate:
        entity = candidate
        try:
            if merge_first:
                entity = await self.session.merge(candidate)
            else:
                self.session.add(candidate)

            for evidence in evidence_list:
                self.session.add(evidence)

            await self.session.commit()
            await self.session.refresh(entity)
            self._expunge(entity)
            return entity
        except SQLAlchemyError:
            await self.session.rollback()
            raise
