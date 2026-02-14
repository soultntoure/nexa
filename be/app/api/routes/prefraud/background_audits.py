"""Background audit API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas.prefraud.background_audit import (
    AuditConfigHistoryResponse,
    AuditConfigResponse,
    AuditConfigUpdateRequest,
    CandidateActionRequest,
    CandidateItem,
    CandidateListResponse,
    RunListItem,
    RunStatusResponse,
    TriggerRunRequest,
    TriggerRunResponse,
)

router = APIRouter(prefix="/background-audits", tags=["background-audits"])


def _get_facade(request: Request):  # type: ignore[no-untyped-def]
    facade = getattr(request.app.state, "background_audit_facade", None)
    if not facade:
        raise HTTPException(503, "Background audit not enabled")
    return facade


@router.post("/trigger", response_model=TriggerRunResponse)
async def trigger_run(
    body: TriggerRunRequest, request: Request,
) -> TriggerRunResponse:
    facade = _get_facade(request)
    run_id = await facade.trigger_run(body.lookback_days, body.run_mode)
    return TriggerRunResponse(run_id=run_id)


@router.get("/runs", response_model=list[RunListItem])
async def list_runs(
    request: Request, skip: int = 0, limit: int = 20,
) -> list[RunListItem]:
    facade = _get_facade(request)
    runs = await facade.list_runs(skip, limit)
    return [RunListItem(**r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str, request: Request,
) -> RunStatusResponse:
    facade = _get_facade(request)
    data = await facade.get_run_status(run_id)
    if "error" in data:
        raise HTTPException(404, "Run not found")
    return RunStatusResponse(**data)


@router.get("/runs/{run_id}/stream")
async def stream_run_progress(run_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint for real-time pipeline progress events."""
    facade = _get_facade(request)
    queue = facade.attach_progress(run_id)

    async def event_generator():  # type: ignore[no-untyped-def]
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break

                data = event.model_dump_json()
                yield f"event: {event.type}\ndata: {data}\n\n"

                if event.type in ("complete", "error"):
                    break
        finally:
            facade.detach_progress(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}/candidates", response_model=CandidateListResponse)
async def get_candidates(
    run_id: str, request: Request, skip: int = 0, limit: int = 50,
) -> CandidateListResponse:
    facade = _get_facade(request)
    items = await facade.get_candidates(run_id, skip, limit)
    return CandidateListResponse(
        run_id=run_id,
        candidates=[CandidateItem(**c) for c in items],
    )


@router.get("/runs/{run_id}/drift-pdf")
async def get_drift_pdf(run_id: str, request: Request) -> StreamingResponse:
    """Generate and return a PDF report for weight drift candidates."""
    from io import BytesIO

    from app.services.background_audit.components.internals.drift_pdf import generate_drift_pdf

    facade = _get_facade(request)
    drift_candidates = await facade.get_drift_candidates(run_id)
    if not drift_candidates:
        raise HTTPException(404, "No drift candidates found for this run")
    card = drift_candidates[0].get("pattern_card", {})
    pdf_bytes = generate_drift_pdf(card)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=drift-report-{run_id}.pdf"},
    )


@router.post("/candidates/{candidate_id}/action")
async def update_candidate_action(
    candidate_id: str,
    body: CandidateActionRequest,
    request: Request,
) -> dict[str, str]:
    facade = _get_facade(request)
    result = await facade.update_candidate_action(candidate_id, body.action)
    if "error" in result:
        raise HTTPException(404, "Candidate not found")
    return result


# --- Config endpoints ---


@router.get("/config", response_model=AuditConfigResponse)
async def get_config(request: Request) -> AuditConfigResponse:
    """Return the active audit config, or defaults if none exists."""
    facade = _get_facade(request)
    data = await facade.get_config()
    return AuditConfigResponse(**data)


@router.put("/config", response_model=AuditConfigResponse)
async def update_config(
    body: AuditConfigUpdateRequest, request: Request,
) -> AuditConfigResponse:
    """Create a new versioned config (partial update merges with active)."""
    facade = _get_facade(request)
    data = await facade.update_config(body.model_dump(exclude_unset=True))
    return AuditConfigResponse(**data)


@router.get("/config/history", response_model=AuditConfigHistoryResponse)
async def get_config_history(
    request: Request, limit: int = 20,
) -> AuditConfigHistoryResponse:
    """Return version history of audit configs."""
    facade = _get_facade(request)
    items = await facade.get_config_history(limit)
    return AuditConfigHistoryResponse(
        configs=[AuditConfigResponse(**c) for c in items],
    )
