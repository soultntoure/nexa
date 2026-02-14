"""
Pattern lifecycle API schemas — request/response models for pattern endpoints.

Contains:
- PatternSummary: Pattern summary for list responses
- PatternListResponse: Paginated pattern list
- MatchedCustomer: Customer matched to a pattern
- PatternDetailResponse: Full pattern detail with matched customers
- PatternActivateRequest / PatternDisableRequest: Lifecycle transition requests
- DetectionRunResponse: Manual detection run result
- GraphNode / GraphEdge / GraphVisualizationResponse: Graph visualization data
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PatternSummary(BaseModel):
    """Pattern summary for list responses."""

    id: uuid.UUID
    pattern_type: str
    description: str
    state: str
    confidence: float = Field(ge=0.0, le=1.0)
    frequency: int
    detected_at: datetime
    last_matched_at: datetime | None = None
    days_since_last_match: int | None = None
    match_count: int


class PatternListResponse(BaseModel):
    """Paginated pattern list."""

    total: int = Field(ge=0)
    patterns: list[PatternSummary]


class MatchedCustomer(BaseModel):
    """Customer matched to a pattern."""

    customer_id: uuid.UUID
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, Any]
    detected_at: datetime


class PatternDetailResponse(BaseModel):
    """Full pattern detail with matched customers."""

    id: uuid.UUID
    pattern_type: str
    description: str
    state: str
    confidence: float = Field(ge=0.0, le=1.0)
    frequency: int
    definition: dict[str, Any]
    evidence: dict[str, Any]
    detected_at: datetime
    last_matched_at: datetime | None = None
    days_since_last_match: int | None = None
    matched_customers: list[MatchedCustomer]


class PatternActivateRequest(BaseModel):
    """Request body for pattern activation."""

    activated_by: uuid.UUID | None = None


class PatternDisableRequest(BaseModel):
    """Request body for pattern disabling."""

    disabled_by: uuid.UUID | None = None
    reason: str | None = None


class DetectionRunResponse(BaseModel):
    """Result of a manual detection run."""

    trigger: str = "manual"
    new_candidates: int
    updated_patterns: int
    skipped_duplicates: int
    total_matches: int
    elapsed_s: float


class GraphNode(BaseModel):
    """Node in a pattern graph visualization."""

    id: str
    type: str
    label: str
    risk_state: str | None = None


class GraphEdge(BaseModel):
    """Edge in a pattern graph visualization."""

    source: str
    target: str
    relation: str


class GraphVisualizationResponse(BaseModel):
    """Graph visualization data with nodes, edges, and metadata."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metadata: dict[str, Any] = Field(default_factory=dict)
