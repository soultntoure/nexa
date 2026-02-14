"""Service layer for threshold configuration CRUD."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.schemas.settings.threshold_config import ThresholdConfigRequest
from app.data.db.models.threshold_config import ThresholdConfig
from app.data.db.repositories.threshold_config_repository import (
    ThresholdConfigRepository,
)

logger = logging.getLogger(__name__)


async def get_active_thresholds(
    session_factory: async_sessionmaker,
) -> ThresholdConfig | None:
    """Return the active threshold config, or None for defaults."""
    async with session_factory() as session:
        repo = ThresholdConfigRepository(session)
        return await repo.get_active()


async def save_thresholds(
    session_factory: async_sessionmaker,
    request: ThresholdConfigRequest,
) -> ThresholdConfig:
    """Create a new active threshold config (deactivates previous)."""
    config = ThresholdConfig(
        approve_below=request.approve_below,
        escalate_below=request.escalate_below,
        indicator_weights=request.indicator_weights,
        updated_by=request.updated_by,
        reason=request.reason,
    )
    async with session_factory() as session:
        repo = ThresholdConfigRepository(session)
        saved = await repo.create_new_config(config)
    logger.info("Threshold config saved: %s", saved.id)
    return saved
