"""Request/response schemas for payout endpoints."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PayoutDecisionRequest(BaseModel):
    """Officer submits a decision on an escalated withdrawal."""

    withdrawal_id: uuid.UUID
    evaluation_id: uuid.UUID | None = Field(None, description="Evaluation run this decision is for")
    officer_id: str = Field(..., min_length=1, description="Officer identifier")
    action: Literal["approved", "blocked"] = Field(..., description="Officer's decision")
    reason: str = Field(..., min_length=1, description="Justification for the decision")


class PayoutDecisionResponse(BaseModel):
    """Confirmation of a submitted decision."""

    withdrawal_id: uuid.UUID
    evaluation_id: uuid.UUID | None
    officer_id: str
    action: str
    reason: str
    decided_at: datetime
    status: Literal["processed"] = "processed"


class BatchDecisionItem(BaseModel):
    """Single item in a batch decision request."""

    withdrawal_id: uuid.UUID
    evaluation_id: uuid.UUID | None = None


class BatchDecisionRequest(BaseModel):
    """Officer submits a batch decision on multiple withdrawals."""

    items: list[BatchDecisionItem] = Field(..., min_length=1, max_length=50)
    officer_id: str = Field(..., min_length=1)
    action: Literal["approved", "blocked"]
    reason: str = Field(..., min_length=1)


class BatchDecisionResultItem(BaseModel):
    """Result for a single item in a batch decision."""

    withdrawal_id: uuid.UUID
    status: Literal["processed", "failed"]
    error: str | None = None


class BatchDecisionResponse(BaseModel):
    """Response for a batch decision request."""

    results: list[BatchDecisionResultItem]
    total: int
    succeeded: int
    failed: int
