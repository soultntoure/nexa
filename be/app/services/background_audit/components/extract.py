"""Extract component — query confirmed-fraud evaluations and build text units."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.background_audit.dataset_prep import (
    RunWindow,
    build_cohort_query,
    compute_text_hash,
    compute_unit_id,
    extract_reasoning_units,
    normalize_text,
    validate_quality,
)
from app.core.background_audit._pii_stubs import mask_pii
from app.data.db.models.audit_text_unit import AuditTextUnit
from app.data.db.repositories.audit_unit_repository import AuditUnitRepository

logger = logging.getLogger(__name__)


async def extract_cohort(
    window: RunWindow,
    session_factory: async_sessionmaker[AsyncSession],
) -> list[AuditTextUnit]:
    """Extract reasoning units from confirmed-fraud evaluations."""
    async with session_factory() as session:
        stmt = build_cohort_query(window.start, window.end)
        result = await session.execute(stmt)
        evaluations = result.scalars().unique().all()

    logger.info("Found %d confirmed-fraud evaluations in window", len(evaluations))
    units: list[AuditTextUnit] = []

    for eval_ in evaluations:
        raw_units = extract_reasoning_units(
            str(eval_.id), str(eval_.withdrawal_id), eval_.investigation_data,
        )
        for raw in raw_units:
            text = normalize_text(raw["text"])
            if not validate_quality(text):
                continue
            masked = mask_pii(text)
            text_hash = compute_text_hash(masked)
            unit_id = compute_unit_id(
                raw["evaluation_id"], raw["source_type"], raw["index"],
            )
            units.append(AuditTextUnit(
                id=uuid.uuid4(),
                unit_id=unit_id,
                evaluation_id=uuid.UUID(raw["evaluation_id"]),
                withdrawal_id=uuid.UUID(raw["withdrawal_id"]),
                source_type=raw["source_type"],
                source_name=raw["source_name"],
                text_masked=masked,
                text_hash=text_hash,
                score=raw.get("score"),
                confidence=raw.get("confidence"),
                vector_status="pending",
            ))

    async with session_factory() as session:
        repo = AuditUnitRepository(session)
        existing_hashes = await repo.get_existing_hashes()
        new_units = [u for u in units if u.text_hash not in existing_hashes]
        inserted = await repo.bulk_upsert_units(new_units)
        logger.info(
            "Extracted %d units, %d new (deduped by hash)", len(units), inserted,
        )

    return units
