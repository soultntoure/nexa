"""Pydantic schemas for the officer review queue endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class QueueIndicator(BaseModel):
    name: str
    display_name: str
    score: float = Field(ge=0.0, le=1.0)
    status: Literal["pass", "warn", "fail"]
    reasoning: str


class RiskAssessment(BaseModel):
    type: Literal["rule_based", "llm_enhanced"]
    indicators: list[QueueIndicator]


class AIRecommendation(BaseModel):
    decision: str
    reasoning: str
    source: Literal["gray_zone_llm", "rule_engine", "investigator"]


class QueueTriageAssignment(BaseModel):
    investigator: str
    priority: str


class QueueTriage(BaseModel):
    constellation_analysis: str
    decision: str = ""
    decision_reasoning: str = ""
    confidence: float = 0.0
    risk_score: float = 0.0
    assignments: list[QueueTriageAssignment]
    elapsed_s: float


class QueueInvestigatorFinding(BaseModel):
    name: str
    score: float
    confidence: float
    reasoning: str
    elapsed_s: float


class QueueInvestigation(BaseModel):
    triage: QueueTriage
    investigators: list[QueueInvestigatorFinding]


class QueueItem(BaseModel):
    withdrawal_id: uuid.UUID
    evaluation_id: uuid.UUID
    customer_id: str = Field(description="External customer ID")
    customer_name: str
    customer_email: str
    amount: float
    currency: str
    requested_at: datetime
    evaluated_at: datetime
    decision: str
    risk_score: float
    risk_level: str
    summary: str
    risk_assessment: RiskAssessment
    ai_recommendation: AIRecommendation
    investigation: QueueInvestigation | None = None


class QueueResponse(BaseModel):
    items: list[QueueItem]
    total: int
