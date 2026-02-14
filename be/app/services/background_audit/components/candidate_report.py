"""Candidate report component — generate candidates from clusters."""

from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data.db.models.audit_candidate import AuditCandidate
from app.services.background_audit.components.embed_cluster import ClusterData
from app.services.background_audit.components.internals.candidate_assembly import (
    CandidateAssemblyService,
)
from app.services.background_audit.components.internals.candidate_investigation import (
    ClusterInvestigationService,
)
from app.services.background_audit.components.internals.candidate_store import (
    CandidatePersistenceService,
)

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Any]


async def generate_candidates(
    clusters: list[ClusterData],
    run_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    agent: Any | None = None,
    max_candidates: int = 50,
    emit: EmitFn | None = None,
    quality_gate_config: dict[str, Any] | None = None,
) -> list[AuditCandidate]:
    """Build candidate pattern cards from qualifying clusters."""
    quality_gate = quality_gate_config or {}
    investigation = ClusterInvestigationService(
        agent=agent,
        emit=emit,
        quality_gate_config=quality_gate,
    )
    qualifying = investigation.select_qualifying(clusters)
    logger.info("Phase 1: %d/%d clusters passed quality gate", len(qualifying), len(clusters))

    results = await investigation.investigate(qualifying)

    persistence = CandidatePersistenceService(session_factory)
    assembly = CandidateAssemblyService(
        run_id=run_id,
        persistence=persistence,
        emit=emit,
        max_candidates=max_candidates,
    )
    candidates = await assembly.assemble(results)
    logger.info("Generated %d candidates from %d investigations", len(candidates), len(qualifying))
    return candidates
