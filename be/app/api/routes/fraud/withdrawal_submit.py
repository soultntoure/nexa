"""
POST /api/withdrawal/submit — create withdrawal + run fraud investigation.

Looks up real customer data from the DB (IP, device, payment method)
so the evaluation correlates with actual stored records.
"""

import logging
import random

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.fraud.fraud_check import FraudCheckRequest, FraudCheckResponse
from app.api.schemas.fraud.withdrawal_submit import WithdrawalSubmitRequest
from app.config import get_settings
from app.core.scoring import ScoringResult
from app.data.db.engine import AsyncSessionLocal, get_session
from app.data.db.models.customer import Customer
from app.data.db.models.device import Device
from app.data.db.models.ip_history import IPHistory
from app.data.db.models.payment_method import PaymentMethod
from app.data.db.models.withdrawal import Withdrawal
from app.services.fraud.internals.response_builder import build_response
from app.services.fraud.investigator_service import InvestigatorService
from app.services.prefraud.posture_scheduler import trigger_recompute

router = APIRouter(prefix="/withdrawal", tags=["withdrawal"])
logger = logging.getLogger(__name__)

settings = get_settings()
SYNC_DB_URI = settings.POSTGRES_URL.replace("+asyncpg", "").split("?")[0]


def _get_service(request: Request) -> InvestigatorService:
    svc = getattr(request.app.state, "investigator_service", None)
    if svc is None:
        svc = InvestigatorService(AsyncSessionLocal, SYNC_DB_URI)
        request.app.state.investigator_service = svc
    return svc


@router.post("/submit", response_model=FraudCheckResponse)
async def submit_withdrawal(
    body: WithdrawalSubmitRequest,
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
    service: InvestigatorService = Depends(_get_service),
) -> FraudCheckResponse:
    """Create a withdrawal row and run fraud investigation."""
    customer = await _lookup_customer(session, body.customer_id)
    payment_method = await _resolve_payment_method(session, customer.id, body.payment_method)
    ip_address = body.ip_address or await _sample_ip(session, customer.id)
    device_fp = body.device_fingerprint or await _sample_device(session, customer.id)

    withdrawal = Withdrawal(
        customer_id=customer.id,
        amount=body.amount,
        currency=body.currency,
        payment_method_id=payment_method.id,
        recipient_name=body.recipient_name,
        recipient_account=body.recipient_account,
        ip_address=ip_address,
        device_fingerprint=device_fp,
        status="pending",
    )
    session.add(withdrawal)
    await session.commit()
    await session.refresh(withdrawal)

    posture_svc = getattr(raw_request.app.state, "posture_service", None)
    if posture_svc:
        trigger_recompute(posture_svc, customer.id, "event:withdrawal_request")

    fraud_request = FraudCheckRequest(
        withdrawal_id=withdrawal.id,
        customer_id=body.customer_id,
        amount=body.amount,
        recipient_name=body.recipient_name,
        recipient_account=body.recipient_account,
        ip_address=ip_address,
        device_fingerprint=device_fp,
        customer_country=customer.country,
    )

    raw = await service.investigate(fraud_request)
    decision = raw["decision"]
    scoring = ScoringResult(
        decision=decision,
        composite_score=raw["risk_score"],
        weighted_breakdown=raw["scoring"].weighted_breakdown,
        reasoning=raw["scoring"].reasoning,
    )
    return build_response(
        evaluation_id=raw["evaluation_id"],
        decision=decision,
        scoring=scoring,
        results=raw["results"],
        elapsed=raw["total_elapsed_s"],
    )


async def _lookup_customer(session: AsyncSession, external_id: str) -> Customer:
    """Find customer by external_id or 404."""
    stmt = select(Customer).where(Customer.external_id == external_id)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {external_id} not found")
    return customer


async def _resolve_payment_method(
    session: AsyncSession, customer_id, method_type: str,
) -> PaymentMethod:
    """Find a matching payment method or fall back to the first one."""
    db_type = "card" if method_type == "bank-card" else "bank_transfer"
    stmt = (
        select(PaymentMethod)
        .where(PaymentMethod.customer_id == customer_id, PaymentMethod.type == db_type)
        .limit(1)
    )
    result = await session.execute(stmt)
    pm = result.scalar_one_or_none()
    if pm:
        return pm

    stmt = select(PaymentMethod).where(PaymentMethod.customer_id == customer_id).limit(1)
    result = await session.execute(stmt)
    pm = result.scalar_one_or_none()
    if not pm:
        raise HTTPException(status_code=404, detail="No payment method found for customer")
    return pm


async def _sample_ip(session: AsyncSession, customer_id) -> str:
    """Pick a random IP from the customer's ip_history."""
    stmt = select(IPHistory.ip_address).where(IPHistory.customer_id == customer_id)
    result = await session.execute(stmt)
    ips = [row[0] for row in result.all()]
    return random.choice(ips) if ips else "127.0.0.1"


async def _sample_device(session: AsyncSession, customer_id) -> str:
    """Pick a random device fingerprint from the customer's devices."""
    stmt = select(Device.fingerprint).where(Device.customer_id == customer_id)
    result = await session.execute(stmt)
    fps = [row[0] for row in result.all()]
    return random.choice(fps) if fps else "unknown-device"
