"""Weight drift analysis phase — runs in parallel with cluster investigation."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.weight_drift import (
    build_drift_summary,
    detect_outliers,
    suggest_countermeasures,
)
from app.data.db.models.audit_candidate import AuditCandidate
from app.data.db.repositories.audit_candidate_repository import AuditCandidateRepository
from app.data.db.repositories.weight_stats_repository import WeightStatsRepository
from app.services.background_audit.components.internals.drift_helpers import (
    build_drift_data,
    build_evidence_text,
    build_pattern_card,
    extract_outlier_tuples,
)

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Any]


async def run_weight_drift_analysis(
    run_id: str,
    window: Any,
    session_factory: async_sessionmaker[AsyncSession],
    agent: Any | None = None,
    emit: EmitFn | None = None,
    max_candidates: int = 5,
) -> list[AuditCandidate]:
    """Run weight drift analysis and persist as AuditCandidate records."""
    if emit:
        await emit("phase_start", {
            "title": "Analyzing weight drift...",
            "phase": "weight_drift",
            "narration": "Checking if indicator weight recalibrations are drifting.",
        })

    async with session_factory() as session:
        repo = WeightStatsRepository(session)
        profiles = await repo.get_profiles_in_interval(window.start, window.end)
        total = await repo.count_recalculations_in_interval(window.start, window.end)

    if not profiles:
        logger.info("No weight profiles in window — skipping drift analysis")
        if emit:
            await emit("progress", {
                "title": "No weight data", "phase": "weight_drift",
                "detail": "No recalibrations in window", "progress": 1.0,
            })
        return []

    summary = build_drift_summary(profiles)
    outlier_tuples = extract_outlier_tuples(profiles)
    outliers = detect_outliers(outlier_tuples)
    countermeasures = suggest_countermeasures(summary)

    for ind in summary.indicators:
        ind.outlier_count = sum(1 for o in outliers if o.indicator_name == ind.name)

    evidence_text = build_evidence_text(summary, outliers, countermeasures, total)

    if emit:
        await emit("hypothesis", {
            "title": "Weight drift detected",
            "narration": f"Found {len(summary.indicators)} indicators across {summary.unique_customers} customers.",
            "phase": "weight_drift",
            "metadata": {"cluster_id": "drift_analysis"},
        })

    agent_result, tool_trace = await _run_agent(agent, evidence_text, emit)
    drift_data = build_drift_data(
        summary, outliers, countermeasures, total,
        window_start=window.start.isoformat(), window_end=window.end.isoformat(),
    )
    pattern_card = build_pattern_card(agent_result, drift_data, tool_trace)

    candidate = await _persist_candidate(run_id, pattern_card, session_factory)

    if emit:
        await emit("candidate", {
            "title": "Weight Drift", "phase": "weight_drift",
            "metadata": {"candidate_id": candidate.candidate_id, "cluster_id": "drift_analysis"},
        })
        await emit("progress", {
            "title": "Drift analysis complete", "phase": "weight_drift",
            "detail": f"{len(countermeasures)} countermeasures identified",
            "progress": 1.0,
        })

    return [candidate]


async def _run_agent(agent: Any, evidence_text: str, emit: EmitFn | None) -> tuple[dict, list]:
    if not agent:
        return {}, []
    agent_result, tool_trace = await agent.analyze(evidence_text)
    if emit:
        for t in tool_trace:
            await emit("agent_tool", {
                "title": str(t.get("tool_name", "tool")),
                "phase": "weight_drift", "metadata": t,
            })
    return agent_result, tool_trace


async def _persist_candidate(
    run_id: str, pattern_card: dict,
    session_factory: async_sessionmaker[AsyncSession],
) -> AuditCandidate:
    candidate = AuditCandidate(
        id=uuid.uuid4(),
        candidate_id=f"{run_id}_drift",
        run_id=run_id,
        status="pending",
        title="Weight Drift Analysis",
        cluster_id="drift_analysis",
        novelty_status="new",
        confidence=0.8,
        support_events=pattern_card["drift_data"]["total_recalibrations"],
        support_accounts=len(pattern_card["drift_data"]["outliers"]),
        quality_score=0.7,
        pattern_card=pattern_card,
    )
    async with session_factory() as session:
        repo = AuditCandidateRepository(session)
        return await repo.create_candidate(candidate)
