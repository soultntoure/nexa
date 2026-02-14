"""
ThresholdConfig CRUD operations.

Contains:
- ThresholdConfigRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> ThresholdConfig | None
  - get_active() -> ThresholdConfig | None
  - create_new_config(config: ThresholdConfig) -> ThresholdConfig
  - get_history(limit: int) -> list[ThresholdConfig]

Rules: async only, only one active config at a time, expunge before return.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.threshold_config import ThresholdConfig
from app.data.db.repositories.base_repository import BaseRepository


class ThresholdConfigRepository(BaseRepository[ThresholdConfig]):
    """Repository for ThresholdConfig entity with versioning support."""

    model_class = ThresholdConfig

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_active(self) -> ThresholdConfig | None:
        """
        Get the currently active threshold configuration.
        
        Returns:
            Active ThresholdConfig (detached), None if no active config exists
        """
        try:
            stmt = select(ThresholdConfig).where(
                ThresholdConfig.is_active == True
            )
            result = await self.session.execute(stmt)
            config = result.scalar_one_or_none()
            
            if config:
                self._expunge(config)
            return config
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving active threshold config") from e

    async def create_new_config(self, config: ThresholdConfig) -> ThresholdConfig:
        """
        Create a new threshold config and deactivate all others.
        
        This implements soft versioning - only one config is active at a time.
        
        Args:
            config: New ThresholdConfig to activate
            
        Returns:
            Created ThresholdConfig (detached)
        """
        try:
            # Deactivate all existing configs
            await self.session.execute(
                update(ThresholdConfig).values(is_active=False)
            )
            
            # Create new active config
            config.is_active = True
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
            self._expunge(config)
            
            return config
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError("Error creating new threshold config") from e

    async def get_history(self, limit: int = 20) -> list[ThresholdConfig]:
        """
        Get configuration history, ordered by created_at (most recent first).
        
        Args:
            limit: Maximum number of configs to return
            
        Returns:
            List of detached ThresholdConfigs
        """
        try:
            stmt = (
                select(ThresholdConfig)
                .order_by(desc(ThresholdConfig.created_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            configs = list(result.scalars().all())
            
            for config in configs:
                self._expunge(config)
            
            return configs
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving config history") from e
