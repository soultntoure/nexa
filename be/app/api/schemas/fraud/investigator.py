"""Request/response schemas for the investigator endpoint."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.fraud.fraud_check import IndicatorDetail, ScoringDetail


class InvestigatorAssignmentDetail(BaseModel):
    """One investigator assignment from the triage router."""

    investigator: str
    priority: str


class TriageDetail(BaseModel):
    """Triage verdict output for the response."""

    constellation_analysis: str
    decision: str
    decision_reasoning: str
    confidence: float
    risk_score: float
    assignments: list[InvestigatorAssignmentDetail]
    elapsed_s: float


class InvestigatorFinding(BaseModel):
    """One investigator's result in the response."""

    investigator_name: str
    display_name: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence: dict[str, object] = Field(default_factory=dict)
    elapsed_s: float


class InvestigatorResponse(BaseModel):
    """Full response from the investigator pipeline."""

    evaluation_id: uuid.UUID
    decision: Literal["approved", "escalated", "blocked"]
    risk_score: float
    risk_percent: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    summary: str
    indicators: list[IndicatorDetail]
    scoring: ScoringDetail
    triage: TriageDetail
    investigators: list[InvestigatorFinding]
    rule_engine_elapsed_s: float
    total_elapsed_s: float
    elapsed_s: float
    checked_at: datetime
