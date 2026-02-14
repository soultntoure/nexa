"""Evidence record builder for candidates (ORM model construction)."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.background_audit.pattern_analysis import rank_evidence
from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence
from app.services.background_audit.components.embed_cluster import ClusterData


def build_evidence_records(
    cluster: ClusterData,
    candidate_id: str,
) -> list[AuditCandidateEvidence]:
    """Create ranked evidence records linking text units to a candidate."""
    unit_by_id = {unit.unit_id: unit for unit in cluster.units}
    raw_units = [
        {
            "unit_id": unit.unit_id,
            "confidence": unit.confidence,
            "score": unit.score,
            "withdrawal_id": str(unit.withdrawal_id),
            "text_preview": unit.text_masked[:200],
        }
        for unit in cluster.units
    ]
    ranked = rank_evidence(raw_units)
    return [
        AuditCandidateEvidence(
            id=uuid.uuid4(),
            candidate_id=candidate_id,
            unit_id=row["unit_id"],
            evidence_type="supporting",
            rank=row["rank"],
            snippet=row.get("text_preview", ""),
            metadata_={
                "confidence": row.get("confidence"),
                "score": row.get("score"),
                "rank_score": row.get("rank_score"),
                "withdrawal_id": row.get("withdrawal_id"),
                "source_name": getattr(unit_by_id.get(row["unit_id"]), "source_name", None),
                "source_type": getattr(unit_by_id.get(row["unit_id"]), "source_type", None),
                "text_preview": row.get("text_preview", ""),
            },
        )
        for row in ranked
    ]
