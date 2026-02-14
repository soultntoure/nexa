"""Schemas for the triage router and investigator results."""

from typing import Literal

from pydantic import BaseModel, Field

InvestigatorName = Literal["financial_behavior", "identity_access", "cross_account"]


class InvestigatorAssignment(BaseModel):
    """A single investigator assignment from the triage router."""

    investigator: InvestigatorName = Field(
        ..., description="Which investigator to invoke."
    )
    priority: Literal["high", "medium", "low"] = Field(
        "medium", description="How urgently this needs investigation."
    )


class TriageResult(BaseModel):
    """Structured output from the triage verdict synthesizer."""

    constellation_analysis: str = Field(
        ...,
        max_length=500,
        description="Brief cross-signal pattern summary (1-2 sentences).",
    )
    decision: Literal["approved", "escalated", "blocked"] = Field(
        ...,
        description="Final verdict: approved, escalated, or blocked.",
    )
    decision_reasoning: str = Field(
        ...,
        max_length=300,
        description="Why this verdict — cite specific investigator evidence.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How certain you are in this decision (0-1).",
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall risk assessment (0 = safe, 1 = high risk).",
    )
    assignments: list[InvestigatorAssignment] = Field(
        default_factory=list,
        description="Which investigators ran (records, not routing).",
    )


class InvestigatorResult(BaseModel):
    """Structured output returned by each consolidated investigator."""

    investigator_name: InvestigatorName = Field(
        ..., description="Which investigator produced this result."
    )
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Risk score: 0.0 = safe, 1.0 = high risk."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="How certain the investigator is."
    )
    reasoning: str = Field(
        ...,
        max_length=300,
        description="2-3 sentences max: evidence found + conclusion. No filler.",
    )
    evidence: dict[str, object] = Field(
        default_factory=dict,
        description="Key metrics and investigative findings.",
    )
