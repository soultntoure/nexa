"""Read-only query methods for background audit facade."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.background_audit.pattern_card import friendly_source_label as _friendly_source_label
from app.data.db.models.audit_config import AuditConfig
from app.data.db.repositories.audit_candidate_repository import AuditCandidateRepository
from app.data.db.repositories.audit_config_repository import AuditConfigRepository
from app.data.db.repositories.audit_evidence_repository import AuditEvidenceRepository
from app.data.db.repositories.audit_run_repository import AuditRunRepository
from app.data.db.repositories.audit_unit_repository import AuditUnitRepository


class BackgroundAuditQueries:
    """Read-only queries for audit runs and candidates."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get_run_status(self, run_id: str) -> dict[str, Any]:
        async with self._sf() as session:
            repo = AuditRunRepository(session)
            run = await repo.get_by_run_id(run_id)
        if not run:
            return {"error": "not_found"}
        return {
            "run_id": run.run_id,
            "status": run.status,
            "counters": run.counters,
            "timings": run.timings,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
        }

    async def list_runs(self, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        async with self._sf() as session:
            repo = AuditRunRepository(session)
            runs = await repo.list_runs(skip, limit)
        return [
            {
                "run_id": r.run_id,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "counters": r.counters,
            }
            for r in runs
        ]

    async def get_candidates(
        self, run_id: str, skip: int = 0, limit: int = 50,
    ) -> list[dict[str, Any]]:
        async with self._sf() as session:
            repo = AuditCandidateRepository(session)
            ev_repo = AuditEvidenceRepository(session)
            candidates = await repo.list_by_run(run_id, skip, limit)
            results = []
            for c in candidates:
                card = c.pattern_card or {}
                evidence = await ev_repo.get_for_candidate(c.candidate_id)
                unit_ids = [e.unit_id for e in evidence if e.unit_id]
                units_by_id: dict[str, Any] = {}
                if unit_ids:
                    unit_repo = AuditUnitRepository(session)
                    units = await unit_repo.get_units_by_ids(unit_ids)
                    units_by_id = {u.unit_id: u for u in units}

                card.pop("tool_trace", None)
                card.pop("evidence_units", None)
                card["ranked_evidence"] = [
                    _serialize_ranked_evidence(e, units_by_id.get(e.unit_id))
                    for e in evidence
                ]
                results.append({
                    "candidate_id": c.candidate_id,
                    "title": c.title,
                    "status": c.status,
                    "quality_score": c.quality_score,
                    "confidence": c.confidence,
                    "support_events": c.support_events,
                    "support_accounts": c.support_accounts,
                    "novelty_status": c.novelty_status,
                    "pattern_card": card,
                })
        return results

    async def update_candidate_action(
        self, candidate_id: str, action: str,
    ) -> dict[str, str]:
        async with self._sf() as session:
            repo = AuditCandidateRepository(session)
            candidate = await repo.get_by_candidate_id(candidate_id)
            if not candidate:
                return {"error": "not_found"}
            if action == "ignore":
                await repo.increment_ignore_count(candidate_id)
            await repo.update_status(candidate_id, action)
        return {"candidate_id": candidate_id, "status": action}

    # --- Config queries ---

    def _config_to_dict(self, config: AuditConfig) -> dict[str, Any]:
        return {
            "id": str(config.id),
            "lookback_days": config.lookback_days,
            "max_candidates": config.max_candidates,
            "output_dir": config.output_dir,
            "min_events": config.min_events,
            "min_accounts": config.min_accounts,
            "min_confidence": config.min_confidence,
            "updated_by": config.updated_by,
            "reason": config.reason,
            "is_active": config.is_active,
            "created_at": config.created_at,
        }

    async def get_config(self) -> dict[str, Any]:
        async with self._sf() as session:
            repo = AuditConfigRepository(session)
            config = await repo.get_active()
        if not config:
            return AuditConfigResponse_defaults()
        return self._config_to_dict(config)

    async def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        async with self._sf() as session:
            repo = AuditConfigRepository(session)
            current = await repo.get_active()
            merged = _merge_config(current, updates)
            created = await repo.create_new_config(merged)
        return self._config_to_dict(created)

    async def get_config_history(self, limit: int = 20) -> list[dict[str, Any]]:
        async with self._sf() as session:
            repo = AuditConfigRepository(session)
            configs = await repo.get_history(limit)
        return [self._config_to_dict(c) for c in configs]


def AuditConfigResponse_defaults() -> dict[str, Any]:
    """Return default config values when no DB row exists."""
    return {
        "id": None,
        "lookback_days": 7,
        "max_candidates": 50,
        "output_dir": "outputs/background_audits/stage_1",
        "min_events": 5,
        "min_accounts": 2,
        "min_confidence": 0.50,
        "updated_by": "system",
        "reason": None,
        "is_active": True,
        "created_at": None,
    }


_CONFIG_FIELDS = (
    "lookback_days", "max_candidates", "output_dir",
    "min_events", "min_accounts", "min_confidence",
)


def _merge_config(current: AuditConfig | None, updates: dict[str, Any]) -> AuditConfig:
    """Merge partial updates with current active config (or defaults)."""
    defaults = AuditConfigResponse_defaults()
    base: dict[str, Any] = {}
    for field in _CONFIG_FIELDS:
        if current:
            base[field] = getattr(current, field)
        else:
            base[field] = defaults[field]

    for field in _CONFIG_FIELDS:
        if field in updates:
            base[field] = updates[field]

    return AuditConfig(
        **base,
        updated_by=updates.get("updated_by", "system"),
        reason=updates.get("reason"),
    )


def _serialize_ranked_evidence(evidence: Any, unit: Any | None) -> dict[str, Any]:
    metadata = evidence.metadata_ or {}
    confidence = _optional_float(metadata.get("confidence"))
    if confidence is None and unit is not None:
        confidence = _optional_float(getattr(unit, "confidence", None))

    score = _optional_float(metadata.get("score"))
    if score is None and unit is not None:
        score = _optional_float(getattr(unit, "score", None))

    rank_score = _optional_float(metadata.get("rank_score"))
    source_name_raw = str(
        metadata.get("source_name")
        or (getattr(unit, "source_name", "") if unit is not None else "")
        or ""
    )
    source_type_raw = str(
        metadata.get("source_type")
        or (getattr(unit, "source_type", "") if unit is not None else "")
        or ""
    )
    source_name = _friendly_source_label(source_name_raw) if source_name_raw else None
    source_type = _friendly_source_label(source_type_raw) if source_type_raw else None
    source = source_name or source_type or _friendly_source_label(evidence.evidence_type)
    withdrawal_id = str(
        metadata.get("withdrawal_id")
        or (getattr(unit, "withdrawal_id", "") if unit is not None else "")
        or ""
    )
    snippet = str(
        evidence.snippet
        or metadata.get("text_preview")
        or (getattr(unit, "text_masked", "") if unit is not None else "")
        or ""
    ).strip()[:500]

    return {
        "unit_id": evidence.unit_id,
        "evidence_type": evidence.evidence_type,
        "rank": evidence.rank,
        "text": snippet,
        "confidence": confidence,
        "score": score,
        "rank_score": rank_score,
        "withdrawal_id": withdrawal_id,
        "source": source,
    }


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


