"""Request/response schemas for the fraud-check endpoint."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FraudCheckRequest(BaseModel):
    """Flat request body with everything the fraud check needs."""

    withdrawal_id: uuid.UUID = Field(..., description="Withdrawal UUID to evaluate")
    customer_id: str = Field(..., description="External ID (e.g. CUST-001)")
    amount: float = Field(..., gt=0, description="Withdrawal amount")
    recipient_name: str
    recipient_account: str
    ip_address: str
    device_fingerprint: str
    customer_country: str = Field(..., min_length=3, max_length=3, description="ISO 3166-1 alpha-3")


class IndicatorDetail(BaseModel):
    """Per-indicator breakdown for the frontend."""

    name: str = Field(description="Internal key (e.g. 'amount_anomaly')")
    display_name: str = Field(description="User-friendly label (e.g. 'Withdrawal Amount')")
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    weight: float
    weighted_score: float
    reasoning: str
    evidence: dict[str, object] = Field(default_factory=dict)
    status: Literal["pass", "warn", "fail"]


class ScoringDetail(BaseModel):
    """Composite scoring metadata."""

    composite_score: float
    decision: str
    reasoning: str
    weighted_breakdown: dict[str, float]
    has_hard_escalation: bool
    has_multi_critical: bool


class GrayZoneLLMDetail(BaseModel):
    """Present only when gray-zone LLM fallback was triggered."""

    decision: str
    reasoning: str
    elapsed_s: float


class LLMIndicatorDetail(BaseModel):
    """Per-indicator result from the LLM-only path."""

    name: str
    display_name: str = ""
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence: dict[str, object] = Field(default_factory=dict)


class LLMComparisonDetail(BaseModel):
    """Present only when run_llm_comparison=True."""

    score: float
    decision: str
    indicators: list[LLMIndicatorDetail]
    elapsed_s: float


class FraudCheckResponse(BaseModel):
    """Full fraud-check response — frontend-friendly."""

    evaluation_id: uuid.UUID = Field(description="Unique ID for this evaluation run")
    decision: Literal["approved", "escalated", "blocked"]
    risk_score: float
    risk_percent: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    summary: str
    indicators: list[IndicatorDetail]
    scoring: ScoringDetail
    gray_zone: GrayZoneLLMDetail | None = None
    llm_comparison: LLMComparisonDetail | None = None
    elapsed_s: float
    checked_at: datetime
