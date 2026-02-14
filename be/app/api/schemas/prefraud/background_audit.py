"""API schemas for background audit endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TriggerRunRequest(BaseModel):
    lookback_days: int | None = Field(None, ge=1, le=365)
    run_mode: str = Field("full", pattern="^(full|incremental)$")


class TriggerRunResponse(BaseModel):
    run_id: str
    status: str = "pending"


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    counters: dict[str, Any] = {}
    timings: dict[str, Any] = {}
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class RunListItem(BaseModel):
    run_id: str
    status: str
    started_at: str | None = None
    counters: dict[str, Any] = {}


class CandidateItem(BaseModel):
    candidate_id: str
    title: str | None = None
    status: str
    quality_score: float
    confidence: float
    support_events: int
    support_accounts: int
    novelty_status: str
    pattern_card: dict[str, Any] = {}


class CandidateListResponse(BaseModel):
    run_id: str
    candidates: list[CandidateItem]


class CandidateActionRequest(BaseModel):
    action: str = Field(..., pattern="^(accepted|rejected|ignore)$")


# --- Audit Config schemas ---


class AuditConfigResponse(BaseModel):
    id: str | None = None
    lookback_days: int = 7
    max_candidates: int = 50
    output_dir: str = "outputs/background_audits/stage_1"
    min_events: int = 5
    min_accounts: int = 2
    min_confidence: float = 0.50
    updated_by: str = "system"
    reason: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class AuditConfigUpdateRequest(BaseModel):
    lookback_days: int | None = Field(None, ge=1, le=365)
    max_candidates: int | None = Field(None, ge=1, le=500)
    output_dir: str | None = None
    min_events: int | None = Field(None, ge=0)
    min_accounts: int | None = Field(None, ge=0)
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    updated_by: str | None = None
    reason: str | None = None


class AuditConfigHistoryResponse(BaseModel):
    configs: list[AuditConfigResponse]
