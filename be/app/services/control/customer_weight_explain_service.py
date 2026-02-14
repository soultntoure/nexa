"""Service to explain customer-specific vs baseline indicator weights."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.control.customer_weights import (
    BlendComparison,
    BlendWeights,
    IndicatorWeightRow,
    WeightHistoryEntry,
    WeightHistoryResponse,
    WeightSnapshotResponse,
)
from app.core.scoring import INDICATOR_WEIGHTS
from app.data.db.models.customer import Customer
from app.data.db.models.customer_weight_profile import CustomerWeightProfile

logger = logging.getLogger(__name__)

_DEFAULT_BLEND = {"rule_engine": 0.6, "investigators": 0.4}
_SAMPLE_THRESHOLD = 5


async def get_snapshot(
    session: AsyncSession, external_id: str,
) -> WeightSnapshotResponse:
    """Build baseline vs customer weight comparison."""
    customer = await _resolve_customer(session, external_id)
    profile = await _get_active_profile(session, customer.id)
    return _build_snapshot(external_id, profile)


async def get_history(
    session: AsyncSession, external_id: str, limit: int = 20,
) -> WeightHistoryResponse:
    """Return recent weight profile history for audit."""
    customer = await _resolve_customer(session, external_id)
    stmt = (
        select(CustomerWeightProfile)
        .where(CustomerWeightProfile.customer_id == customer.id)
        .order_by(CustomerWeightProfile.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    entries = [
        WeightHistoryEntry(
            timestamp=r.recalculated_at,
            indicator_weights=r.indicator_weights,
            blend_weights=r.blend_weights,
            is_active=r.is_active,
        )
        for r in rows
    ]
    return WeightHistoryResponse(customer_id=external_id, entries=entries)


async def reset_to_baseline(
    session: AsyncSession,
    external_id: str,
    reason: str,
    updated_by: str,
) -> str:
    """Deactivate active profile, restoring baseline behavior."""
    customer = await _resolve_customer(session, external_id)
    profile = await _get_active_profile(session, customer.id)
    if not profile:
        return "No active profile to reset."

    stmt = (
        select(CustomerWeightProfile)
        .where(
            CustomerWeightProfile.customer_id == customer.id,
            CustomerWeightProfile.is_active.is_(True),
        )
    )
    result = await session.execute(stmt)
    active = result.scalar_one_or_none()
    if active:
        active.is_active = False
        await session.commit()
        logger.info(
            "Reset profile for %s by %s: %s", external_id, updated_by, reason,
        )
    return f"Profile reset to baseline for {external_id}."


# ── Private helpers ──


async def _resolve_customer(
    session: AsyncSession, external_id: str,
) -> Customer:
    """Look up customer by external_id or raise."""
    stmt = select(Customer).where(Customer.external_id == external_id)
    customer = (await session.execute(stmt)).scalar_one_or_none()
    if not customer:
        raise ValueError(f"Customer {external_id} not found")
    return customer


async def _get_active_profile(
    session: AsyncSession, customer_id: uuid.UUID,
) -> CustomerWeightProfile | None:
    """Get single active weight profile."""
    stmt = select(CustomerWeightProfile).where(
        CustomerWeightProfile.customer_id == customer_id,
        CustomerWeightProfile.is_active.is_(True),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _build_snapshot(
    external_id: str,
    profile: CustomerWeightProfile | None,
) -> WeightSnapshotResponse:
    """Assemble the comparison payload."""
    baseline_blend = BlendWeights(**_DEFAULT_BLEND)

    if profile:
        cust_blend = BlendWeights(**profile.blend_weights)
        multipliers = profile.indicator_weights
        window = profile.decision_window
        sample = len(window)
        # Support both "decision" (seeded data) and "officer_action" (runtime data)
        approvals = sum(
            1 for d in window
            if d.get("officer_action") == "approved" or d.get("decision") == "approved"
        )
        blocks = sum(
            1 for d in window
            if d.get("officer_action") == "blocked" or d.get("decision") == "blocked"
        )
        status = "applied" if sample >= _SAMPLE_THRESHOLD else "limited data"
        last_updated = profile.recalculated_at
    else:
        cust_blend = baseline_blend
        multipliers = {}
        sample = approvals = blocks = 0
        status = "baseline fallback"
        last_updated = None

    indicators = _build_indicator_rows(multipliers, sample)

    return WeightSnapshotResponse(
        customer_id=external_id,
        personalization_status=status,
        last_updated=last_updated,
        sample_count=sample,
        approval_count=approvals,
        block_count=blocks,
        blend=BlendComparison(baseline=baseline_blend, customer=cust_blend),
        indicators=indicators,
    )


def _build_indicator_rows(
    multipliers: dict, sample: int,
) -> list[IndicatorWeightRow]:
    """One row per indicator with baseline, customer, diff, status."""
    rows: list[IndicatorWeightRow] = []
    for name, baseline_w in INDICATOR_WEIGHTS.items():
        mult = multipliers.get(name, {})
        customer_mult = mult.get("multiplier", 1.0) if isinstance(mult, dict) else float(mult) if mult else 1.0
        customer_w = round(baseline_w * customer_mult, 4)
        diff = round(customer_w - baseline_w, 4)
        reason = mult.get("reason", "") if isinstance(mult, dict) else ""

        if abs(diff) < 0.001:
            row_status = "baseline fallback"
        elif sample >= _SAMPLE_THRESHOLD:
            row_status = "stable"
        else:
            row_status = "limited data"

        rows.append(IndicatorWeightRow(
            name=name,
            baseline_weight=baseline_w,
            customer_multiplier=customer_mult,
            customer_weight=customer_w,
            difference=diff,
            status=row_status,
            reason=reason,
        ))
    rows.sort(key=lambda r: abs(r.difference), reverse=True)
    return rows
