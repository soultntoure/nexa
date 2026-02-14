"""
Pattern lifecycle endpoints — list, detail, activate, disable, detect, graph.

Endpoints:
  GET  /api/patterns                          — List with state/type filters
  GET  /api/patterns/{id}                     — Detail with matched customers
  POST /api/patterns/{id}/activate            — CANDIDATE/DISABLED -> ACTIVE
  POST /api/patterns/{id}/disable             — ACTIVE/CANDIDATE -> DISABLED
  POST /api/patterns/detect                   — Trigger manual detection run
  GET  /api/patterns/{id}/graph               — Pattern graph visualization
  GET  /api/customers/{customer_id}/network   — Customer-centric graph view
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import and_, select, func

from app.api.schemas.prefraud.pattern import (
    DetectionRunResponse,
    GraphEdge,
    GraphNode,
    GraphVisualizationResponse,
    MatchedCustomer,
    PatternActivateRequest,
    PatternDetailResponse,
    PatternDisableRequest,
    PatternListResponse,
    PatternSummary,
)
from app.data.db.engine import AsyncSessionLocal
from app.data.db.models.customer import Customer
from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.data.db.models.device import Device
from app.data.db.models.fraud_pattern import FraudPattern
from app.data.db.models.ip_history import IPHistory
from app.data.db.models.pattern_match import PatternMatch
from app.data.db.repositories.pattern_match_repository import PatternMatchRepository
from app.data.db.repositories.pattern_repository import PatternRepository

logger = logging.getLogger(__name__)

# ── Routers ──

pattern_router = APIRouter(prefix="/patterns", tags=["patterns"])
customer_network_router = APIRouter(
    prefix="/customers/{customer_id}/network",
    tags=["patterns"],
)


# ── Helpers ──

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _days_since(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    delta = _utcnow() - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else _utcnow() - dt
    return max(0, delta.days)


def _to_summary(pattern: FraudPattern, match_count: int) -> PatternSummary:
    return PatternSummary(
        id=pattern.id,
        pattern_type=pattern.pattern_type,
        description=pattern.description,
        state=pattern.state,
        confidence=pattern.confidence,
        frequency=pattern.frequency,
        detected_at=pattern.detected_at,
        last_matched_at=pattern.last_matched_at,
        days_since_last_match=_days_since(pattern.last_matched_at),
        match_count=match_count,
    )


def _to_detail(
    pattern: FraudPattern,
    matched_customers: list[MatchedCustomer],
) -> PatternDetailResponse:
    return PatternDetailResponse(
        id=pattern.id,
        pattern_type=pattern.pattern_type,
        description=pattern.description,
        state=pattern.state,
        confidence=pattern.confidence,
        frequency=pattern.frequency,
        definition=pattern.definition,
        evidence=pattern.evidence,
        detected_at=pattern.detected_at,
        last_matched_at=pattern.last_matched_at,
        days_since_last_match=_days_since(pattern.last_matched_at),
        matched_customers=matched_customers,
    )


# ── Pattern List ──

@pattern_router.get("", response_model=PatternListResponse)
async def list_patterns(
    state: str | None = Query(default=None, description="Filter by state"),
    pattern_type: str | None = Query(default=None, description="Filter by pattern type"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PatternListResponse:
    """List patterns with optional state/type filters."""
    async with AsyncSessionLocal() as session:
        pattern_repo = PatternRepository(session)
        match_repo = PatternMatchRepository(session)

        if state and pattern_type:
            all_patterns = await pattern_repo.get_by_type_and_state(
                pattern_type, [state],
            )
        elif state:
            all_patterns = await pattern_repo.get_by_state(state)
        elif pattern_type:
            all_patterns = await pattern_repo.get_by_type_and_state(
                pattern_type, ["candidate", "active", "disabled"],
            )
        else:
            all_patterns = await pattern_repo.list_all(skip=0, limit=10_000)

        total = len(all_patterns)
        page = all_patterns[offset : offset + limit]

        summaries = []
        for p in page:
            count = await match_repo.count_by_pattern(p.id)
            summaries.append(_to_summary(p, count))

    return PatternListResponse(total=total, patterns=summaries)


# ── Pattern Detail ──

@pattern_router.get("/{pattern_id}", response_model=PatternDetailResponse)
async def get_pattern_detail(pattern_id: uuid.UUID) -> PatternDetailResponse:
    """Get pattern detail including matched customers."""
    async with AsyncSessionLocal() as session:
        pattern_repo = PatternRepository(session)
        match_repo = PatternMatchRepository(session)

        pattern = await pattern_repo.get_by_id(pattern_id)
        if pattern is None:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")

        matches = await match_repo.get_by_pattern(pattern_id)

    matched_customers = [
        MatchedCustomer(
            customer_id=m.customer_id,
            confidence=m.confidence,
            evidence=m.evidence,
            detected_at=m.detected_at,
        )
        for m in matches
    ]

    return _to_detail(pattern, matched_customers)


# ── Activate ──

@pattern_router.post("/{pattern_id}/activate", response_model=PatternDetailResponse)
async def activate_pattern(
    pattern_id: uuid.UUID,
    body: PatternActivateRequest | None = None,
) -> PatternDetailResponse:
    """Transition CANDIDATE -> ACTIVE or DISABLED -> ACTIVE."""
    async with AsyncSessionLocal() as session:
        pattern_repo = PatternRepository(session)
        match_repo = PatternMatchRepository(session)

        try:
            pattern = await pattern_repo.activate(
                pattern_id,
                activated_by=body.activated_by if body else None,
            )
        except ValueError as exc:
            if "not found" in str(exc):
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        matches = await match_repo.get_by_pattern(pattern_id)

    matched_customers = [
        MatchedCustomer(
            customer_id=m.customer_id,
            confidence=m.confidence,
            evidence=m.evidence,
            detected_at=m.detected_at,
        )
        for m in matches
    ]

    return _to_detail(pattern, matched_customers)


# ── Disable ──

@pattern_router.post("/{pattern_id}/disable", response_model=PatternDetailResponse)
async def disable_pattern(
    pattern_id: uuid.UUID,
    body: PatternDisableRequest | None = None,
) -> PatternDetailResponse:
    """Transition ACTIVE -> DISABLED or CANDIDATE -> DISABLED."""
    async with AsyncSessionLocal() as session:
        pattern_repo = PatternRepository(session)
        match_repo = PatternMatchRepository(session)

        try:
            pattern = await pattern_repo.disable(
                pattern_id,
                disabled_by=body.disabled_by if body else None,
                reason=body.reason if body else None,
            )
        except ValueError as exc:
            if "not found" in str(exc):
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        matches = await match_repo.get_by_pattern(pattern_id)

    matched_customers = [
        MatchedCustomer(
            customer_id=m.customer_id,
            confidence=m.confidence,
            evidence=m.evidence,
            detected_at=m.detected_at,
        )
        for m in matches
    ]

    return _to_detail(pattern, matched_customers)


# ── Manual Detection Run ──

@pattern_router.post("/detect", response_model=DetectionRunResponse)
async def trigger_detection(request: Request) -> DetectionRunResponse:
    """Trigger a manual detection run across all detectors."""
    detection_service = getattr(request.app.state, "detection_service", None)
    if detection_service is None:
        raise HTTPException(
            status_code=503,
            detail="Detection service is not configured",
        )

    t0 = time.perf_counter()

    try:
        result = await detection_service.run_detection()
    except Exception as exc:
        logger.exception("Manual detection run failed")
        raise HTTPException(
            status_code=500, detail=f"Detection run failed: {exc}",
        ) from exc

    elapsed = round(time.perf_counter() - t0, 2)

    return DetectionRunResponse(
        trigger="manual",
        new_candidates=result.new_candidates,
        updated_patterns=result.updated_patterns,
        skipped_duplicates=result.skipped_duplicates,
        total_matches=result.total_matches,
        elapsed_s=elapsed,
    )


# ── Pattern Graph Visualization ──

@pattern_router.get("/{pattern_id}/graph", response_model=GraphVisualizationResponse)
async def get_pattern_graph(pattern_id: uuid.UUID) -> GraphVisualizationResponse:
    """Graph visualization data (nodes + edges) for a pattern."""
    async with AsyncSessionLocal() as session:
        pattern_repo = PatternRepository(session)
        match_repo = PatternMatchRepository(session)

        pattern = await pattern_repo.get_by_id(pattern_id)
        if pattern is None:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")

        matches = await match_repo.get_by_pattern(pattern_id)
        if not matches:
            return GraphVisualizationResponse(nodes=[], edges=[], metadata={})

        customer_ids = [m.customer_id for m in matches]
        customers = await _load_customer_map(session, customer_ids)
        postures = await _load_posture_map(session, customer_ids)
        shared_devices, shared_ips = await _load_shared_entities(
            session, customer_ids,
        )

    return _build_graph(
        pattern, matches, customers, postures, shared_devices, shared_ips,
    )


# ── Customer Network View ──

@customer_network_router.get("", response_model=GraphVisualizationResponse)
async def get_customer_network(customer_id: uuid.UUID) -> GraphVisualizationResponse:
    """Customer-centric network — all patterns this customer belongs to."""
    async with AsyncSessionLocal() as session:
        match_repo = PatternMatchRepository(session)
        pattern_repo = PatternRepository(session)

        customer_matches = await match_repo.get_current_by_customer(customer_id)
        if not customer_matches:
            return GraphVisualizationResponse(nodes=[], edges=[], metadata={})

        # Collect all sibling matches across all patterns
        all_customer_ids: set[uuid.UUID] = {customer_id}
        pattern_matches_map: dict[uuid.UUID, list[PatternMatch]] = {}
        patterns: dict[uuid.UUID, FraudPattern] = {}

        for cm in customer_matches:
            pattern = await pattern_repo.get_by_id(cm.pattern_id)
            if pattern is None:
                continue
            patterns[pattern.id] = pattern
            siblings = await match_repo.get_by_pattern(cm.pattern_id)
            pattern_matches_map[pattern.id] = siblings
            for s in siblings:
                all_customer_ids.add(s.customer_id)

        customer_id_list = list(all_customer_ids)
        customers = await _load_customer_map(session, customer_id_list)
        postures = await _load_posture_map(session, customer_id_list)
        shared_devices, shared_ips = await _load_shared_entities(
            session, customer_id_list,
        )

    # Merge graphs from all patterns
    all_nodes: dict[str, GraphNode] = {}
    all_edges: list[GraphEdge] = []
    all_entity_types: set[str] = set()

    for pid, p in patterns.items():
        graph = _build_graph(
            p,
            pattern_matches_map[pid],
            customers,
            postures,
            shared_devices,
            shared_ips,
        )
        for node in graph.nodes:
            all_nodes[node.id] = node
        all_edges.extend(graph.edges)
        all_entity_types.update(graph.metadata.get("shared_entity_types", []))

    # Deduplicate edges
    seen_edges: set[tuple[str, str, str]] = set()
    unique_edges: list[GraphEdge] = []
    for edge in all_edges:
        key = (edge.source, edge.target, edge.relation)
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    return GraphVisualizationResponse(
        nodes=list(all_nodes.values()),
        edges=unique_edges,
        metadata={
            "center_customer": str(customer_id),
            "pattern_count": len(patterns),
            "shared_entity_types": sorted(all_entity_types),
        },
    )


# ── Graph helpers (private) ──

async def _load_customer_map(
    session,
    customer_ids: list[uuid.UUID],
) -> dict[uuid.UUID, Customer]:
    """Batch-load customers by ID."""
    if not customer_ids:
        return {}
    stmt = select(Customer).where(Customer.id.in_(customer_ids))
    result = await session.execute(stmt)
    return {c.id: c for c in result.scalars().all()}


async def _load_posture_map(
    session,
    customer_ids: list[uuid.UUID],
) -> dict[uuid.UUID, CustomerRiskPosture]:
    """Batch-load current postures for customers."""
    if not customer_ids:
        return {}
    stmt = select(CustomerRiskPosture).where(
        and_(
            CustomerRiskPosture.customer_id.in_(customer_ids),
            CustomerRiskPosture.is_current == True,
        )
    )
    result = await session.execute(stmt)
    return {p.customer_id: p for p in result.scalars().all()}


async def _load_shared_entities(
    session,
    customer_ids: list[uuid.UUID],
) -> tuple[dict[str, list[uuid.UUID]], dict[str, list[uuid.UUID]]]:
    """Load shared devices and IPs among the given customers.

    Returns:
        (shared_devices, shared_ips) where each is
        {entity_id: [customer_ids that share it]}.
    """
    if not customer_ids:
        return {}, {}

    # Shared device fingerprints
    device_stmt = (
        select(Device.fingerprint, Device.customer_id)
        .where(Device.customer_id.in_(customer_ids))
    )
    device_result = await session.execute(device_stmt)
    device_map: dict[str, list[uuid.UUID]] = defaultdict(list)
    for row in device_result:
        device_map[row.fingerprint].append(row.customer_id)
    shared_devices = {
        fp: cids for fp, cids in device_map.items() if len(set(cids)) >= 2
    }

    # Shared IP addresses
    ip_stmt = (
        select(IPHistory.ip_address, IPHistory.customer_id)
        .where(IPHistory.customer_id.in_(customer_ids))
    )
    ip_result = await session.execute(ip_stmt)
    ip_map: dict[str, list[uuid.UUID]] = defaultdict(list)
    for row in ip_result:
        ip_map[row.ip_address].append(row.customer_id)
    shared_ips = {
        ip: cids for ip, cids in ip_map.items() if len(set(cids)) >= 2
    }

    return shared_devices, shared_ips


def _build_graph(
    pattern: FraudPattern,
    matches: list[PatternMatch],
    customers: dict[uuid.UUID, Customer],
    postures: dict[uuid.UUID, CustomerRiskPosture],
    shared_devices: dict[str, list[uuid.UUID]],
    shared_ips: dict[str, list[uuid.UUID]],
) -> GraphVisualizationResponse:
    """Build graph visualization from pattern data."""
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    customer_ids = {m.customer_id for m in matches}

    # Customer nodes
    for m in matches:
        cust = customers.get(m.customer_id)
        posture = postures.get(m.customer_id)
        node_id = str(m.customer_id)
        nodes[node_id] = GraphNode(
            id=node_id,
            type="customer",
            label=cust.name if cust else node_id,
            risk_state=posture.posture if posture else None,
        )

    # Device nodes + edges
    for fp, cids in shared_devices.items():
        matched_cids = [c for c in set(cids) if c in customer_ids]
        if len(matched_cids) < 2:
            continue
        dev_node_id = f"dev-{fp[:8]}"
        nodes[dev_node_id] = GraphNode(
            id=dev_node_id, type="device", label=f"Device {fp[:8]}",
        )
        for cid in matched_cids:
            edges.append(GraphEdge(
                source=str(cid), target=dev_node_id, relation="shared_device",
            ))

    # IP nodes + edges
    for ip, cids in shared_ips.items():
        matched_cids = [c for c in set(cids) if c in customer_ids]
        if len(matched_cids) < 2:
            continue
        ip_node_id = f"ip-{ip}"
        nodes[ip_node_id] = GraphNode(
            id=ip_node_id, type="ip", label=ip,
        )
        for cid in matched_cids:
            edges.append(GraphEdge(
                source=str(cid), target=ip_node_id, relation="shared_ip",
            ))

    # Collect shared entity types
    entity_types: set[str] = set()
    if shared_devices:
        entity_types.add("device")
    if shared_ips:
        entity_types.add("ip_address")

    return GraphVisualizationResponse(
        nodes=list(nodes.values()),
        edges=edges,
        metadata={
            "ring_size": len(matches),
            "shared_entity_types": sorted(entity_types),
            "pattern_confidence": pattern.confidence,
        },
    )
