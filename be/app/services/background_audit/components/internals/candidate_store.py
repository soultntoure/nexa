"""Candidate persistence adapter for report generation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.background_audit.pattern_analysis import calculate_candidate_quality
from app.data.db.models.audit_candidate import AuditCandidate
from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence
from app.data.db.repositories.audit_candidate_repository import AuditCandidateRepository
from app.services.background_audit.components.candidate_utils import (
    build_evidence_records,
    evidence_quality,
)
from app.services.background_audit.components.embed_cluster import ClusterData


class CandidatePersistenceService:
    """Persist candidate writes through repository-only DB operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load_existing_candidates(self) -> list[AuditCandidate]:
        """Load all non-deleted candidates for cross-run dedup."""
        async with self._session_factory() as session:
            repo = AuditCandidateRepository(session)
            stmt = (
                select(AuditCandidate)
                .where(AuditCandidate.status != "deleted")
                .order_by(AuditCandidate.quality_score.desc())
            )
            result = await session.execute(stmt)
            entities = list(result.scalars().all())
            for e in entities:
                session.expunge(e)
            return entities

    async def create_candidate(
        self,
        run_id: str,
        cluster: ClusterData,
        pattern_card: dict[str, Any],
        conf: float,
        events: int,
        accounts: int,
    ) -> AuditCandidate:
        candidate_id = f"{run_id}_{cluster.cluster_id}"
        candidate = self._build_candidate(
            run_id=run_id,
            candidate_id=candidate_id,
            cluster=cluster,
            pattern_card=pattern_card,
            conf=conf,
            events=events,
            accounts=accounts,
        )
        evidence_units = self._build_evidence(cluster, candidate_id)

        async with self._session_factory() as session:
            repo = AuditCandidateRepository(session)
            return await repo.create_with_evidence(candidate, evidence_units)

    async def persist_merged_candidate(
        self,
        candidate: AuditCandidate,
        cluster: ClusterData,
    ) -> AuditCandidate:
        evidence_units = self._build_evidence(cluster, candidate.candidate_id)
        async with self._session_factory() as session:
            repo = AuditCandidateRepository(session)
            return await repo.update_with_evidence(candidate, evidence_units)

    @staticmethod
    def _build_evidence(
        cluster: ClusterData,
        candidate_id: str,
    ) -> list[AuditCandidateEvidence]:
        return build_evidence_records(cluster, candidate_id)

    @staticmethod
    def _build_candidate(
        run_id: str,
        candidate_id: str,
        cluster: ClusterData,
        pattern_card: dict[str, Any],
        conf: float,
        events: int,
        accounts: int,
    ) -> AuditCandidate:
        quality = calculate_candidate_quality(
            confidence=conf,
            support_events=events,
            support_accounts=accounts,
            evidence_quality=evidence_quality(cluster.units),
        )
        pattern_name = pattern_card.get("formal_pattern_name", "Unknown")
        title = pattern_name if pattern_name != "Unknown" else f"Pattern {cluster.cluster_id}"
        return AuditCandidate(
            id=uuid.uuid4(),
            candidate_id=candidate_id,
            run_id=run_id,
            status="pending",
            title=title,
            cluster_id=cluster.cluster_id,
            novelty_status=cluster.novelty.status,
            matched_cluster_id=cluster.novelty.matched_cluster_id,
            confidence=conf,
            support_events=events,
            support_accounts=accounts,
            quality_score=quality,
            pattern_card=pattern_card,
        )
