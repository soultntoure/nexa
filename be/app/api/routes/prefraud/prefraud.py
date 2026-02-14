"""
Pre-fraud posture endpoints — read, recompute, and query posture history.

Endpoints:
  GET  /api/customers/{customer_id}/risk-posture             — Current posture
  POST /api/customers/{customer_id}/risk-posture/recompute   — Manual recompute
  GET  /api/customers/{customer_id}/risk-posture/history      — Posture history
  POST /api/prefraud/recompute-all                            — Bulk recompute
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import Counter

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas.prefraud.posture import (
    PostureHistoryResponse,
    PostureResponse,
    PostureSnapshotResponse,
    RecomputeAllResult,
)
from app.data.db.engine import AsyncSessionLocal
from app.data.db.repositories.posture_repository import PostureRepository
from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.services.prefraud.posture_service import PostureService

logger = logging.getLogger(__name__)

# ── Routers ──

customer_posture_router = APIRouter(
    prefix="/customers/{customer_id}/risk-posture",
    tags=["prefraud"],
)

prefraud_router = APIRouter(prefix="/prefraud", tags=["prefraud"])


# ── Dependency ──

def _get_posture_service(request: Request) -> PostureService:
    """Lazy-load PostureService from app.state, cache for reuse."""
    svc = getattr(request.app.state, "posture_service", None)
    if svc is None:
        svc = PostureService(AsyncSessionLocal)
        request.app.state.posture_service = svc
    return svc


# ── Helpers ──

def _to_response(posture: CustomerRiskPosture) -> PostureResponse:
    """Convert ORM model to API response."""
    evidence = posture.signal_evidence or {}
    return PostureResponse(
        customer_id=posture.customer_id,
        posture=posture.posture,
        composite_score=posture.composite_score,
        signal_scores=posture.signal_scores,
        top_reasons=evidence.get("top_reasons", []),
        trigger=posture.trigger,
        computed_at=posture.computed_at,
    )


def _to_snapshot(posture: CustomerRiskPosture) -> PostureSnapshotResponse:
    """Convert ORM model to history snapshot response."""
    evidence = posture.signal_evidence or {}
    return PostureSnapshotResponse(
        posture=posture.posture,
        composite_score=posture.composite_score,
        signal_scores=posture.signal_scores,
        top_reasons=evidence.get("top_reasons", []),
        trigger=posture.trigger,
        computed_at=posture.computed_at,
    )


# ── Customer Posture Endpoints ──

@customer_posture_router.get("", response_model=PostureResponse)
async def get_current_posture(
    customer_id: uuid.UUID,
    request: Request,
) -> PostureResponse:
    """Get the current risk posture for a customer."""
    svc = _get_posture_service(request)
    posture = await svc.get_current(customer_id)

    if posture is None:
        raise HTTPException(
            status_code=404,
            detail=f"No posture computed yet for customer {customer_id}",
        )

    return _to_response(posture)


@customer_posture_router.post("/recompute", response_model=PostureResponse)
async def recompute_posture(
    customer_id: uuid.UUID,
    request: Request,
) -> PostureResponse:
    """Trigger synchronous posture recompute and return the new posture."""
    svc = _get_posture_service(request)

    try:
        posture = await svc.recompute(customer_id, trigger="manual")
    except Exception as exc:
        logger.exception("Posture recompute failed for %s", customer_id)
        raise HTTPException(
            status_code=500,
            detail=f"Posture recompute failed: {exc}",
        ) from exc

    return _to_response(posture)


@customer_posture_router.get("/history", response_model=PostureHistoryResponse)
async def get_posture_history(
    customer_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PostureHistoryResponse:
    """Get posture snapshot history for a customer, most recent first."""
    async with AsyncSessionLocal() as session:
        repo = PostureRepository(session)
        total = await repo.count_history(customer_id)
        snapshots = await repo.get_history(customer_id, limit=limit, offset=offset)

    return PostureHistoryResponse(
        customer_id=customer_id,
        total=total,
        snapshots=[_to_snapshot(s) for s in snapshots],
    )


# ── Bulk Recompute Endpoint ──

@prefraud_router.post("/recompute-all", response_model=RecomputeAllResult)
async def recompute_all_postures(request: Request) -> RecomputeAllResult:
    """Trigger bulk posture recompute for all active customers."""
    svc = _get_posture_service(request)

    t0 = time.perf_counter()
    snapshots = await svc.recompute_all(trigger="manual")
    elapsed = round(time.perf_counter() - t0, 2)

    counts: Counter[str] = Counter(s.posture for s in snapshots)

    return RecomputeAllResult(
        total_customers=len(snapshots),
        results={
            "normal": counts.get("normal", 0),
            "watch": counts.get("watch", 0),
            "high_risk": counts.get("high_risk", 0),
        },
        elapsed_s=elapsed,
    )
