"""Candidate dedupe and persistence orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from app.core.background_audit.candidate_metrics import avg_confidence, evidence_quality
from app.core.background_audit.merge_logic import (
    initialize_dedupe_metadata,
    merge_candidate_card,
    should_skip_pattern,
)
from app.core.background_audit.pattern_analysis import calculate_candidate_quality
from app.core.background_audit.signature_matching import (
    CandidateSignature,
    build_candidate_signature,
    match_duplicate_candidate,
    merge_signatures,
)
from app.data.db.models.audit_candidate import AuditCandidate
from app.services.background_audit.components.internals.candidate_investigation import (
    InvestigationResult,
)
from app.services.background_audit.components.internals.candidate_store import (
    CandidatePersistenceService,
)

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Any]


@dataclass(slots=True)
class CandidateBuildState:
    candidates: list[AuditCandidate]
    seen: dict[str, AuditCandidate]
    signatures: dict[str, CandidateSignature]


class CandidateAssemblyService:
    """Phase 3: dedupe investigated clusters into persisted candidates."""

    def __init__(
        self,
        run_id: str,
        persistence: CandidatePersistenceService,
        emit: EmitFn | None,
        max_candidates: int,
    ) -> None:
        self._run_id = run_id
        self._persistence = persistence
        self._emit = emit
        self._max_candidates = max_candidates

    async def assemble(
        self,
        results: list[InvestigationResult | BaseException],
    ) -> list[AuditCandidate]:
        state = CandidateBuildState(candidates=[], seen={}, signatures={})
        await self._load_existing_signatures(state)
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Investigation failed: %s", result)
                continue
            created = await self._process_result(result, state)
            if created and len(state.candidates) >= self._max_candidates:
                break
        return state.candidates

    async def _load_existing_signatures(self, state: CandidateBuildState) -> None:
        """Pre-load signatures from previous runs for cross-run dedup."""
        existing = await self._persistence.load_existing_candidates()
        for c in existing:
            sig = build_candidate_signature(
                candidate_id=c.candidate_id,
                pattern_card=c.pattern_card or {},
                centroid=(),
            )
            state.seen[c.candidate_id] = c
            state.signatures[c.candidate_id] = sig
        if existing:
            logger.info("Loaded %d existing candidates for cross-run dedup", len(existing))

    async def _process_result(
        self,
        result: InvestigationResult,
        state: CandidateBuildState,
    ) -> bool:
        cluster, pattern_card, conf, events, accounts = result
        pattern_name = pattern_card.get("formal_pattern_name", "Unknown")
        if should_skip_pattern(pattern_name):
            return False

        candidate_id = f"{self._run_id}_{cluster.cluster_id}"
        centroid = tuple(float(v) for v in cluster.centroid)
        sig = build_candidate_signature(
            candidate_id=candidate_id, pattern_card=pattern_card, centroid=centroid,
        )
        match_id, reason, metrics = match_duplicate_candidate(state.signatures, sig)

        if match_id:
            await self._merge_into(match_id, cluster, pattern_card, sig, candidate_id, reason, metrics or {}, events, accounts, state)
            return False

        await self._create_new(cluster, pattern_card, candidate_id, centroid, sig, conf, events, accounts, pattern_name, state)
        return True

    async def _merge_into(
        self,
        match_id: str,
        cluster: Any,
        pattern_card: dict[str, Any],
        sig: CandidateSignature,
        candidate_id: str,
        reason: str | None,
        metrics: dict[str, Any],
        events: int,
        accounts: int,
        state: CandidateBuildState,
    ) -> None:
        existing = state.seen[match_id]
        base_events = existing.support_events
        eq = evidence_quality(cluster.units)

        card = existing.pattern_card or {}
        existing.pattern_card = card
        initialize_dedupe_metadata(
            pattern_card=card, candidate_id=existing.candidate_id,
            cluster_id=existing.cluster_id or cluster.cluster_id, evidence_score=eq,
        )
        existing.support_events += events
        existing.support_accounts += accounts
        existing.confidence = max(existing.confidence, avg_confidence(cluster.units))
        card["support_events"] = existing.support_events
        card["support_accounts"] = existing.support_accounts

        merged_clusters = card["merged_clusters"]
        if cluster.cluster_id not in merged_clusters:
            merged_clusters.append(cluster.cluster_id)
        card["deduped_cluster_count"] = len(merged_clusters)
        deduped = card["deduped_candidate_ids"]
        if candidate_id not in deduped:
            deduped.append(candidate_id)

        merge_candidate_card(
            card, pattern_card,
            incoming_candidate_id=candidate_id, cluster_id=cluster.cluster_id,
            dedupe_reason=reason or "semantic_duplicate",
            similarity_metrics=metrics, incoming_evidence_quality=eq,
        )
        _recalculate_quality(existing, eq)

        updated = await self._persistence.persist_merged_candidate(existing, cluster)
        state.seen[updated.candidate_id] = updated
        state.signatures[updated.candidate_id] = merge_signatures(
            state.signatures[updated.candidate_id], sig,
            base_support_events=base_events, incoming_support_events=events,
        )
        _replace_in_list(state.candidates, updated)
        await self._emit_event(updated, cluster.cluster_id, events, accounts, reason, metrics)

    async def _create_new(
        self,
        cluster: Any,
        pattern_card: dict[str, Any],
        candidate_id: str,
        centroid: tuple[float, ...],
        sig: CandidateSignature,
        conf: float,
        events: int,
        accounts: int,
        pattern_name: str,
        state: CandidateBuildState,
    ) -> None:
        initialize_dedupe_metadata(
            pattern_card=pattern_card, candidate_id=candidate_id,
            cluster_id=cluster.cluster_id, evidence_score=evidence_quality(cluster.units),
        )
        candidate = await self._persistence.create_candidate(
            run_id=self._run_id, cluster=cluster,
            pattern_card=pattern_card, conf=conf, events=events, accounts=accounts,
        )
        state.candidates.append(candidate)
        state.seen[candidate.candidate_id] = candidate
        state.signatures[candidate.candidate_id] = build_candidate_signature(
            candidate_id=candidate.candidate_id,
            pattern_card=candidate.pattern_card, centroid=centroid,
        )
        await self._emit_event(candidate, cluster.cluster_id, events, accounts)

    async def _emit_event(
        self,
        candidate: AuditCandidate,
        cluster_id: str,
        events: int,
        accounts: int,
        dedupe_reason: str | None = None,
        dedupe_metrics: dict[str, Any] | None = None,
    ) -> None:
        if not self._emit:
            return
        payload: dict[str, Any] = {
            "candidate_id": candidate.candidate_id,
            "title": candidate.title,
            "quality": candidate.quality_score,
            "pattern_name": candidate.title,
            "cluster_id": cluster_id,
            "event_count": events,
            "account_count": accounts,
        }
        if dedupe_reason:
            payload["dedupe_reason"] = dedupe_reason
            payload["dedupe_metrics"] = dedupe_metrics
        await self._emit("candidate", payload)


def _replace_in_list(candidates: list[AuditCandidate], updated: AuditCandidate) -> None:
    for idx, c in enumerate(candidates):
        if c.candidate_id == updated.candidate_id:
            candidates[idx] = updated
            return


def _recalculate_quality(candidate: AuditCandidate, incoming_eq: float) -> None:
    eq = float(candidate.pattern_card.get("evidence_quality_max", incoming_eq))
    quality = calculate_candidate_quality(
        confidence=candidate.confidence,
        support_events=candidate.support_events,
        support_accounts=candidate.support_accounts,
        evidence_quality=eq,
    )
    candidate.quality_score = max(candidate.quality_score, quality)
