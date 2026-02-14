"""Repository for audit_text_units table."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.audit_text_unit import AuditTextUnit
from app.data.db.repositories.base_repository import BaseRepository


class AuditUnitRepository(BaseRepository[AuditTextUnit]):
    model_class = AuditTextUnit

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def bulk_upsert_units(
        self, units: list[AuditTextUnit],
    ) -> int:
        """Upsert units by unit_id. Returns count of inserted."""
        if not units:
            return 0
        count = 0
        for unit in units:
            stmt = (
                insert(AuditTextUnit)
                .values(
                    id=unit.id,
                    unit_id=unit.unit_id,
                    evaluation_id=unit.evaluation_id,
                    withdrawal_id=unit.withdrawal_id,
                    source_type=unit.source_type,
                    source_name=unit.source_name,
                    text_masked=unit.text_masked,
                    text_hash=unit.text_hash,
                    score=unit.score,
                    confidence=unit.confidence,
                    decision_snapshot=unit.decision_snapshot,
                    embedding_model_name=unit.embedding_model_name,
                    vector_status=unit.vector_status,
                )
                .on_conflict_do_nothing(index_elements=["unit_id"])
            )
            result = await self.session.execute(stmt)
            count += result.rowcount
        await self.session.commit()
        return count

    async def get_existing_hashes(self) -> set[str]:
        stmt = select(AuditTextUnit.text_hash)
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_units_by_ids(
        self, unit_ids: list[str],
    ) -> list[AuditTextUnit]:
        if not unit_ids:
            return []
        stmt = select(AuditTextUnit).where(
            AuditTextUnit.unit_id.in_(unit_ids),
        )
        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())
        for e in entities:
            self._expunge(e)
        return entities

    async def mark_vector_status(
        self, unit_ids: list[str], status: str,
    ) -> None:
        if not unit_ids:
            return
        stmt = (
            update(AuditTextUnit)
            .where(AuditTextUnit.unit_id.in_(unit_ids))
            .values(vector_status=status)
        )
        await self.session.execute(stmt)
        await self.session.commit()
