"""Schemas for threshold configuration settings endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ThresholdConfigRequest(BaseModel):
    """Request to update scoring thresholds."""

    approve_below: float = Field(30.0, ge=0, le=100)
    escalate_below: float = Field(70.0, ge=0, le=100)
    indicator_weights: dict[str, float] = Field(default_factory=dict)
    updated_by: str = "system"
    reason: str | None = None


class ThresholdConfigResponse(BaseModel):
    """Active threshold configuration returned to frontend."""

    id: uuid.UUID
    approve_below: float
    escalate_below: float
    indicator_weights: dict[str, float]
    updated_by: str
    reason: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
