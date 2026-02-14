"""Response schemas for the investigate endpoint."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CustomerSummary(BaseModel):
    name: str
    external_id: str
    country: str
    registration_date: datetime
    is_flagged: bool


class RecentWithdrawal(BaseModel):
    amount: Decimal
    currency: str
    status: str
    recipient_name: str
    requested_at: datetime


class IPRecord(BaseModel):
    ip_address: str
    location: str | None
    is_vpn: bool
    last_seen_at: datetime


class DeviceRecord(BaseModel):
    fingerprint: str
    os: str | None
    browser: str | None
    is_trusted: bool
    last_seen_at: datetime


class InvestigateResponse(BaseModel):
    customer: CustomerSummary
    recent_withdrawals: list[RecentWithdrawal]
    ip_history: list[IPRecord]
    devices: list[DeviceRecord]
