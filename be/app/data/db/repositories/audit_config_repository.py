"""
AuditConfig CRUD operations.

Contains:
- AuditConfigRepository class (takes AsyncSession)
  - get_active() -> AuditConfig | None
  - create_new_config(config) -> AuditConfig (deactivates all, activates new)
  - get_history(limit) -> list[AuditConfig]

Rules: async only, only one active config at a time, expunge before return.
"""

from __future__ import annotations

from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.audit_config import AuditConfig
from app.data.db.repositories.base_repository import BaseRepository


class AuditConfigRepository(BaseRepository[AuditConfig]):
    """Repository for AuditConfig entity with versioning support."""

    model_class = AuditConfig

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_active(self) -> AuditConfig | None:
        """Get the currently active audit configuration."""
        try:
            stmt = select(AuditConfig).where(AuditConfig.is_active == True)
            result = await self.session.execute(stmt)
            config = result.scalar_one_or_none()
            if config:
                self._expunge(config)
            return config
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving active audit config") from e

    async def create_new_config(self, config: AuditConfig) -> AuditConfig:
        """Create a new audit config and deactivate all others."""
        try:
            await self.session.execute(
                update(AuditConfig).values(is_active=False)
            )
            config.is_active = True
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
            self._expunge(config)
            return config
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError("Error creating new audit config") from e

    async def get_history(self, limit: int = 20) -> list[AuditConfig]:
        """Get configuration history, most recent first."""
        try:
            stmt = (
                select(AuditConfig)
                .order_by(desc(AuditConfig.created_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            configs = list(result.scalars().all())
            for config in configs:
                self._expunge(config)
            return configs
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving audit config history") from e
