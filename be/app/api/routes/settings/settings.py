"""Settings endpoint — read/write scoring thresholds."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.schemas.settings.threshold_config import (
    ThresholdConfigRequest,
    ThresholdConfigResponse,
)
from app.core.scoring import APPROVE_THRESHOLD, BLOCK_THRESHOLD, INDICATOR_WEIGHTS
from app.data.db.engine import AsyncSessionLocal
from app.services.control.threshold_service import (
    get_active_thresholds,
    save_thresholds,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["settings"])


def _default_response() -> dict:
    """Build default response when no DB config exists."""
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "approve_below": APPROVE_THRESHOLD * 100,
        "escalate_below": BLOCK_THRESHOLD * 100,
        "indicator_weights": INDICATOR_WEIGHTS,
        "updated_by": "system",
        "reason": "Default configuration",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@router.get("/settings")
async def get_settings() -> dict:
    """Return the active threshold config or defaults."""
    config = await get_active_thresholds(AsyncSessionLocal)
    if config is None:
        return _default_response()
    return ThresholdConfigResponse.model_validate(config).model_dump(mode="json")


@router.post("/settings")
async def update_settings(request: ThresholdConfigRequest) -> dict:
    """Save a new threshold configuration."""
    saved = await save_thresholds(AsyncSessionLocal, request)
    return ThresholdConfigResponse.model_validate(saved).model_dump(mode="json")
