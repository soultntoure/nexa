"""Request schema for the withdrawal submission endpoint."""

from pydantic import BaseModel, Field


class WithdrawalSubmitRequest(BaseModel):
    """Everything the frontend sends when a user submits a withdrawal."""

    customer_id: str = Field(..., description="External ID (e.g. CUST-001)")
    amount: float = Field(..., gt=0, description="Withdrawal amount")
    currency: str = Field(default="USD", max_length=3)
    payment_method: str = Field(..., description="bank-card | bank-transfer")
    recipient_name: str = Field(..., min_length=1)
    recipient_account: str = Field(..., min_length=1)
    ip_address: str = Field(default="", description="Optional — sampled from DB if empty")
    device_fingerprint: str = Field(default="", description="Optional — sampled from DB if empty")
