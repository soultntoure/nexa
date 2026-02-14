"""
Schemas for transaction history listing.

Contains:
- TransactionHistoryItem: single row in the history table
- TransactionHistoryResponse: paginated list of items
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TransactionHistoryItem(BaseModel):
    id: uuid.UUID
    customer_name: str
    email: str
    amount: Decimal
    currency: str
    date: datetime
    status: str
    is_fraud: bool | None

    model_config = {"from_attributes": True}


class TransactionHistoryResponse(BaseModel):
    items: list[TransactionHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
