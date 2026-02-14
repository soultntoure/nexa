"""Customer weight explanation routes — officer-facing."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.control.customer_weights import (
    WeightHistoryResponse,
    WeightResetRequest,
    WeightResetResponse,
    WeightSnapshotResponse,
)
from app.data.db.engine import get_session
from app.services.control import customer_weight_explain_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/customers",
    tags=["customer-weights"],
)


@router.get(
    "/{external_id}/weights",
    response_model=WeightSnapshotResponse,
)
async def get_weight_snapshot(
    external_id: str,
    session: AsyncSession = Depends(get_session),
) -> WeightSnapshotResponse:
    """Return baseline vs customer weight comparison for the drawer."""
    try:
        return await svc.get_snapshot(session, external_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{external_id}/weights/history",
    response_model=WeightHistoryResponse,
)
async def get_weight_history(
    external_id: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> WeightHistoryResponse:
    """Return weight profile history for audit."""
    try:
        return await svc.get_history(session, external_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{external_id}/weights/reset",
    response_model=WeightResetResponse,
)
async def reset_weights(
    external_id: str,
    body: WeightResetRequest,
    session: AsyncSession = Depends(get_session),
) -> WeightResetResponse:
    """Reset customer to baseline weights."""
    try:
        message = await svc.reset_to_baseline(
            session, external_id, body.reason, body.updated_by,
        )
        return WeightResetResponse(
            customer_id=external_id, message=message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
