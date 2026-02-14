"""Detector: shared device/IP/recipient fraud rings via recursive CTE.

Uses PostgreSQL recursive CTEs with CYCLE clause for multi-hop graph traversal.
Column reference: devices.fingerprint (NOT device_fingerprint).
Post-processing uses union-find to group edges into connected components.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.detectors.base import PatternMatchResult

_RING_QUERY = """
WITH RECURSIVE
-- Step 1: Build the shared entity graph (seed)
shared_entities AS (
    -- Shared devices (fingerprint column, not device_fingerprint)
    SELECT fingerprint AS entity_id, 'device' AS entity_type, customer_id
    FROM devices
    WHERE fingerprint IN (
        SELECT fingerprint FROM devices
        GROUP BY fingerprint HAVING COUNT(DISTINCT customer_id) >= 2
    )
    UNION ALL
    -- Shared IPs
    SELECT ip_address AS entity_id, 'ip' AS entity_type, customer_id
    FROM ip_history
    WHERE ip_address IN (
        SELECT ip_address FROM ip_history
        GROUP BY ip_address HAVING COUNT(DISTINCT customer_id) >= 3
    )
    UNION ALL
    -- Shared recipients
    SELECT recipient_account AS entity_id, 'recipient' AS entity_type, customer_id
    FROM withdrawals
    WHERE recipient_account IN (
        SELECT recipient_account FROM withdrawals
        GROUP BY recipient_account HAVING COUNT(DISTINCT customer_id) >= 2
    )
),

-- Step 2: Recursive expansion to find connected components
entity_graph AS (
    -- Base: direct connections from seed
    SELECT
        a.customer_id AS source_customer,
        b.customer_id AS target_customer,
        a.entity_type,
        a.entity_id,
        1 AS depth
    FROM shared_entities a
    JOIN shared_entities b
        ON a.entity_id = b.entity_id
        AND a.entity_type = b.entity_type
        AND a.customer_id != b.customer_id

    UNION

    -- Recursive: follow shared entities to linked customers
    SELECT
        eg.source_customer,
        se.customer_id AS target_customer,
        se.entity_type,
        se.entity_id,
        eg.depth + 1
    FROM entity_graph eg
    JOIN shared_entities se
        ON eg.target_customer IN (
            SELECT se2.customer_id FROM shared_entities se2
            WHERE se2.entity_id = se.entity_id
              AND se2.entity_type = se.entity_type
        )
        AND se.customer_id != eg.source_customer
    WHERE eg.depth < 4  -- Depth guard: max 4 hops
)
CYCLE source_customer, target_customer SET is_cycle USING path

-- Step 3: Extract connected components
SELECT DISTINCT
    source_customer,
    target_customer,
    entity_type,
    entity_id,
    depth
FROM entity_graph
WHERE NOT is_cycle;
"""


class SharedDeviceRingDetector:
    """Recursive CTE detector for shared device/IP/recipient fraud rings."""

    pattern_type = "shared_device_ring"

    async def detect(self, session: AsyncSession) -> list[PatternMatchResult]:
        result = await session.execute(text(_RING_QUERY))
        rows = result.mappings().all()

        if not rows:
            return []

        return _build_ring_matches(rows)


def _build_ring_matches(rows: list | Sequence) -> list[PatternMatchResult]:
    """Group raw edge rows into connected components via union-find."""
    parent: dict[UUID, UUID] = {}

    def find(x: UUID) -> UUID:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a: UUID, b: UUID) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            # Use smaller UUID as root for deterministic group_key
            if str(ra) < str(rb):
                parent[rb] = ra
            else:
                parent[ra] = rb

    # Track edge metadata per customer pair
    edge_entity_types: dict[tuple[UUID, UUID], set[str]] = defaultdict(set)
    edge_max_depth: dict[tuple[UUID, UUID], int] = defaultdict(int)

    for row in rows:
        src = UUID(str(row["source_customer"]))
        tgt = UUID(str(row["target_customer"]))

        parent.setdefault(src, src)
        parent.setdefault(tgt, tgt)
        union(src, tgt)

        key = (min(src, tgt, key=str), max(src, tgt, key=str))
        edge_entity_types[key].add(row["entity_type"])
        edge_max_depth[key] = max(edge_max_depth[key], int(row["depth"]))

    # Group into connected components
    components: dict[UUID, set[UUID]] = defaultdict(set)
    for node in parent:
        root = find(node)
        components[root].add(node)

    # Collect entity types and max depth per component
    component_entity_types: dict[UUID, set[str]] = defaultdict(set)
    component_max_depth: dict[UUID, int] = defaultdict(int)

    for (a, _), etypes in edge_entity_types.items():
        root = find(a)
        component_entity_types[root].update(etypes)

    for (a, _), depth in edge_max_depth.items():
        root = find(a)
        component_max_depth[root] = max(component_max_depth[root], depth)

    # Yield PatternMatchResult per member
    matches: list[PatternMatchResult] = []
    for group_root, members in components.items():
        if len(members) < 2:
            continue

        group_key = str(min(members, key=str))
        entity_types = sorted(component_entity_types.get(group_root, set()))
        max_depth = component_max_depth.get(group_root, 1)
        confidence = _compute_ring_confidence(members, entity_types)

        for customer_id in members:
            matches.append(
                PatternMatchResult(
                    customer_id=customer_id,
                    confidence=round(confidence, 4),
                    evidence={
                        "ring_size": len(members),
                        "linked_customers": [
                            str(m) for m in members if m != customer_id
                        ],
                        "shared_entity_types": entity_types,
                        "ring_depth": max_depth,
                    },
                    group_key=group_key,
                ),
            )

    return matches


def _compute_ring_confidence(members: set[UUID], entity_types: list[str]) -> float:
    """Confidence increases with ring size and number of shared entity types."""
    size_factor = min(len(members) / 5.0, 1.0)  # Saturates at 5 members
    type_factor = len(entity_types) / 3.0  # 3 entity types max
    return min(0.95, 0.5 + size_factor * 0.25 + type_factor * 0.2)
