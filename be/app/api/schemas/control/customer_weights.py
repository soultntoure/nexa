"""Schemas for customer weight explanation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BlendWeights(BaseModel):
    rule_engine: float = 0.6
    investigators: float = 0.4


class BlendComparison(BaseModel):
    baseline: BlendWeights
    customer: BlendWeights


class IndicatorWeightRow(BaseModel):
    name: str
    baseline_weight: float
    customer_multiplier: float = 1.0
    customer_weight: float
    difference: float
    status: str = "baseline fallback"
    reason: str = ""


class WeightSnapshotResponse(BaseModel):
    customer_id: str
    personalization_status: str = "baseline fallback"
    last_updated: datetime | None = None
    sample_count: int = 0
    blend: BlendComparison
    indicators: list[IndicatorWeightRow]


class WeightHistoryEntry(BaseModel):
    timestamp: datetime
    indicator_weights: dict[str, Any]
    blend_weights: dict[str, float]
    is_active: bool


class WeightHistoryResponse(BaseModel):
    customer_id: str
    entries: list[WeightHistoryEntry]


class WeightResetRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    updated_by: str = Field(..., min_length=1)


class WeightResetResponse(BaseModel):
    customer_id: str
    status: str = "reset_to_baseline"
    message: str
