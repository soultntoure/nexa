"""
Transaction history endpoints — queries REAL DB data.

GET  /api/transactions         - Paginated withdrawal history with evaluations
GET  /api/transactions/export  - Download as CSV
"""

import io
import csv
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.engine import get_session
from app.data.db.models.customer import Customer
from app.data.db.models.evaluation import Evaluation
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.models.payment_method import PaymentMethod
from app.data.db.models.withdrawal import Withdrawal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

INDICATOR_ICONS = {
    "amount_anomaly": "lucide:trending-up",
    "velocity": "lucide:gauge",
    "payment_method": "lucide:credit-card",
    "geographic": "lucide:map-pin",
    "device_fingerprint": "lucide:smartphone",
    "trading_behavior": "lucide:bar-chart-3",
    "recipient": "lucide:user-check",
    "card_errors": "lucide:alert-triangle",
}

INDICATOR_DISPLAY = {
    "amount_anomaly": "Withdrawal Amount",
    "velocity": "Transaction Velocity",
    "payment_method": "Payment Method Risk",
    "geographic": "Geographic Analysis",
    "device_fingerprint": "Device Fingerprint",
    "trading_behavior": "Trading Behavior",
    "recipient": "Recipient Analysis",
    "card_errors": "Card Error Patterns",
}

INVESTIGATOR_DISPLAY = {
    "financial_behavior": "Financial Behavior Analyst",
    "identity_access": "Identity & Access Analyst",
    "cross_account": "Cross-Account Analyst",
}

PM_TYPE_MAP = {
    "card": "card",
    "bank_transfer": "bank",
    "ewallet": "ewallet",
    "crypto": "crypto",
}


def _format_withdrawal(w: Withdrawal, eval_row: Evaluation | None, indicators: list[IndicatorResult]) -> dict:
    """Format a withdrawal + evaluation into the rich shape the FE expects."""
    customer = w.customer
    pm = w.payment_method

    risk_score = eval_row.composite_score if eval_row else 0.0
    risk_level = "low"
    if risk_score >= 0.7:
        risk_level = "critical"
    elif risk_score >= 0.5:
        risk_level = "high"
    elif risk_score >= 0.3:
        risk_level = "medium"

    status = w.status or "pending"
    if eval_row and status == "pending":
        status = eval_row.decision

    reg_date = customer.registration_date if customer else None
    account_age = (datetime.now(timezone.utc) - reg_date).days if reg_date else 0

    formatted_indicators = []
    for ind in indicators:
        formatted_indicators.append({
            "name": ind.indicator_name,
            "icon": INDICATOR_ICONS.get(ind.indicator_name, "lucide:help-circle"),
            "score": round(ind.score, 3),
            "weight": round(ind.weight, 3),
            "confidence": round(ind.confidence, 3),
            "reasoning": ind.reasoning or "",
            "evidence": ind.evidence or {},
        })

    triage_data = None
    investigators_data = None
    if eval_row and eval_row.investigation_data:
        inv_data = eval_row.investigation_data
        if "triage" in inv_data:
            triage_data = inv_data["triage"]
        if "investigators" in inv_data:
            investigators_data = [
                {
                    "investigator_name": inv["name"],
                    "display_name": INVESTIGATOR_DISPLAY.get(inv["name"], inv["name"]),
                    "score": round(inv["score"], 3),
                    "confidence": round(inv["confidence"], 3),
                    "reasoning": inv.get("reasoning", ""),
                    "elapsed_s": round(inv.get("elapsed_s", 0), 2),
                }
                for inv in inv_data["investigators"]
            ]

    return {
        "id": f"TXN-{str(w.id)[:8].upper()}",
        "withdrawal_id": str(w.id),
        "evaluation_id": str(eval_row.id) if eval_row else None,
        "customer": {
            "external_id": customer.external_id if customer else "",
            "name": customer.name if customer else "Unknown",
            "email": customer.email if customer else "",
            "country": customer.country if customer else "",
            "registration_date": reg_date.isoformat() if reg_date else "",
            "account_age_days": account_age,
            "total_deposits": 0,
            "total_withdrawals": 0,
            "account_type": "Standard",
        },
        "amount": float(w.amount),
        "currency": w.currency,
        "payment_method": PM_TYPE_MAP.get(pm.type, pm.type) if pm else "bank",
        "recipient": {
            "name": w.recipient_name,
            "account_number": w.recipient_account,
            "bank": "",
        },
        "ip_address": w.ip_address,
        "device": w.device_fingerprint,
        "risk_score": round(risk_score, 3),
        "risk_level": risk_level,
        "status": status,
        "indicators": formatted_indicators,
        "triage": triage_data,
        "investigators": investigators_data,
        "created_at": w.requested_at.isoformat() if w.requested_at else "",
        "updated_at": (w.processed_at or w.requested_at or w.created_at).isoformat(),
    }


@router.get("")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="Filter by name or email"),
    status: str | None = Query(None, description="Filter by status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Paginated withdrawal history with real DB data."""
    try:
        # Build base query
        stmt = (
            select(Withdrawal)
            .join(Customer, Withdrawal.customer_id == Customer.id)
            .options(
                joinedload(Withdrawal.customer),
                joinedload(Withdrawal.payment_method),
            )
            .order_by(desc(Withdrawal.requested_at))
        )

        count_stmt = (
            select(func.count())
            .select_from(Withdrawal)
            .join(Customer, Withdrawal.customer_id == Customer.id)
        )

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Customer.name.ilike(pattern) | Customer.email.ilike(pattern)
            )
            count_stmt = count_stmt.where(
                Customer.name.ilike(pattern) | Customer.email.ilike(pattern)
            )

        if status and status != "all":
            stmt = stmt.where(Withdrawal.status == status)
            count_stmt = count_stmt.where(Withdrawal.status == status)

        total = (await session.execute(count_stmt)).scalar_one()
        offset = (page - 1) * page_size
        rows = (
            await session.execute(stmt.offset(offset).limit(page_size))
        ).scalars().unique().all()

        # Fetch evaluations and indicators for these withdrawals
        withdrawal_ids = [w.id for w in rows]

        evals_map: dict = {}
        indicators_map: dict = {}

        if withdrawal_ids:
            eval_stmt = select(Evaluation).where(
                Evaluation.withdrawal_id.in_(withdrawal_ids)
            ).order_by(desc(Evaluation.checked_at))
            eval_rows = (await session.execute(eval_stmt)).scalars().all()
            for e in eval_rows:
                if e.withdrawal_id not in evals_map:
                    evals_map[e.withdrawal_id] = e

            eval_ids = [e.id for e in evals_map.values()]
            if eval_ids:
                ind_stmt = select(IndicatorResult).where(
                    IndicatorResult.evaluation_id.in_(eval_ids)
                )
                ind_rows = (await session.execute(ind_stmt)).scalars().all()
                for ind in ind_rows:
                    indicators_map.setdefault(ind.evaluation_id, []).append(ind)

        items = []
        for w in rows:
            ev = evals_map.get(w.id)
            inds = indicators_map.get(ev.id, []) if ev else []
            items.append(_format_withdrawal(w, ev, inds))

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
        }
    except Exception as exc:
        logger.exception("list_transactions error: %s", exc)
        return {"items": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 1}


@router.get("/export")
async def export_transactions_csv(
    search: str | None = Query(None),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Download real transaction history as CSV."""
    try:
        stmt = (
            select(Withdrawal)
            .join(Customer, Withdrawal.customer_id == Customer.id)
            .options(
                joinedload(Withdrawal.customer),
                joinedload(Withdrawal.payment_method),
            )
            .order_by(desc(Withdrawal.requested_at))
        )
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Customer.name.ilike(pattern) | Customer.email.ilike(pattern)
            )
        if status and status != "all":
            stmt = stmt.where(Withdrawal.status == status)

        rows = (await session.execute(stmt)).scalars().unique().all()

        # Get evaluations
        wids = [w.id for w in rows]
        evals_map = {}
        if wids:
            eval_rows = (await session.execute(
                select(Evaluation).where(Evaluation.withdrawal_id.in_(wids))
                .order_by(desc(Evaluation.checked_at))
            )).scalars().all()
            for e in eval_rows:
                if e.withdrawal_id not in evals_map:
                    evals_map[e.withdrawal_id] = e

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Customer", "Email", "Amount", "Currency", "Method", "Risk Score", "Status", "Date"])
        for w in rows:
            ev = evals_map.get(w.id)
            c = w.customer
            pm = w.payment_method
            writer.writerow([
                str(w.id)[:8],
                c.name if c else "",
                c.email if c else "",
                float(w.amount),
                w.currency,
                pm.type if pm else "",
                round(ev.composite_score, 3) if ev else 0,
                w.status,
                w.requested_at.isoformat() if w.requested_at else "",
            ])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )
    except Exception as exc:
        logger.exception("export_transactions_csv error: %s", exc)
        buf = io.StringIO()
        buf.write("Error exporting data")
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )
