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
