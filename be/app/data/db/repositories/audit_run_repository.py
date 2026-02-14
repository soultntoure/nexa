"""Repository for audit_runs table."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.audit_run import AuditRun
from app.data.db.repositories.base_repository import BaseRepository


class AuditRunRepository(BaseRepository[AuditRun]):
    model_class = AuditRun

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_run_id(self, run_id: str) -> AuditRun | None:
        stmt = select(AuditRun).where(AuditRun.run_id == run_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            self._expunge(entity)
        return entity

    async def get_by_idempotency_key(self, key: str) -> AuditRun | None:
        stmt = select(AuditRun).where(AuditRun.idempotency_key == key)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            self._expunge(entity)
        return entity

    async def update_status(
        self, run_id: str, status: str, **kwargs: object,
    ) -> None:
        values: dict[str, object] = {"status": status}
        if status in ("completed", "failed"):
            values["completed_at"] = datetime.now(timezone.utc)
        if "error_message" in kwargs:
            values["error_message"] = kwargs["error_message"]
        if "counters" in kwargs:
            values["counters"] = kwargs["counters"]
        if "timings" in kwargs:
            values["timings"] = kwargs["timings"]

        stmt = update(AuditRun).where(AuditRun.run_id == run_id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_heartbeat(self, run_id: str) -> None:
        stmt = (
            update(AuditRun)
            .where(AuditRun.run_id == run_id)
            .values(last_heartbeat_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def list_runs(
        self, skip: int = 0, limit: int = 20,
    ) -> list[AuditRun]:
        stmt = (
            select(AuditRun)
            .order_by(AuditRun.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())
        for e in entities:
            self._expunge(e)
        return entities
