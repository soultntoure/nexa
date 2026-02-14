"""
Posture API schemas — request/response models for pre-fraud posture endpoints.

Contains:
- PostureResponse: Current posture for a customer
- PostureSnapshotResponse: Single history entry
- PostureHistoryResponse: Paginated history list
- RecomputeAllResponse: Bulk recompute summary
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PostureResponse(BaseModel):
    """Current posture state for a single customer."""

    customer_id: uuid.UUID = Field(description="Customer UUID")
    posture: Literal["normal", "watch", "high_risk"] = Field(
        description="Current risk posture state"
    )
    composite_score: float = Field(
        ge=0.0, le=1.0, description="Weighted composite of all signals"
    )
    signal_scores: dict[str, float] = Field(
        description="Per-signal scores (0.0–1.0)"
    )
    top_reasons: list[str] = Field(
        description="Top 3 contributing risk reasons"
    )
    trigger: str = Field(
        description="What triggered this computation (e.g. 'manual', 'scheduled', 'event:new_device')"
    )
    computed_at: datetime = Field(description="When this posture was computed")


class PostureSnapshotResponse(BaseModel):
    """Single posture snapshot in history."""

    posture: Literal["normal", "watch", "high_risk"]
    composite_score: float = Field(ge=0.0, le=1.0)
    signal_scores: dict[str, float]
    top_reasons: list[str]
    trigger: str
    computed_at: datetime


class PostureHistoryResponse(BaseModel):
    """Paginated posture history for a customer."""

    customer_id: uuid.UUID
    total: int = Field(ge=0, description="Total number of snapshots")
    snapshots: list[PostureSnapshotResponse]


class RecomputeAllResult(BaseModel):
    """Summary of bulk posture recomputation."""

    total_customers: int
    results: dict[str, int] = Field(
        description="Count per posture state {'normal': N, 'watch': N, 'high_risk': N}"
    )
    elapsed_s: float = Field(description="Wall-clock seconds for full recompute")
