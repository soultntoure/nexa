"""
Graph Proximity signal — detects shared infrastructure with other customers.

Sub-signals:
- Customers sharing same device fingerprint: 0 safe, >= 2 risky
- Customers sharing same IP address (30d): 0 safe, >= 3 risky
- Customers sharing same recipient account: 0 safe, >= 1 risky
- Any shared-entity customer is_flagged: no safe, yes instant 0.9

Second-degree exposure is logged as evidence only, not scored.
Detection scope is "direct_entity_sharing_only" (V1 limitation).

Inputs: devices, ip_history, withdrawals, customers.is_flagged
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.signals.base import BaseSignal, SignalResult, _linear_score


class GraphProximitySignal(BaseSignal):
    """Scores direct infrastructure sharing with other customers."""

    name = "graph_proximity"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        data = await _fetch_graph_data(customer_id, session)
        score, evidence, reason = _compute_score(data)
        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )


async def _fetch_graph_data(
    customer_id: uuid.UUID, session: AsyncSession,
) -> dict:
    """Fetch shared entity counts and flagged connection info."""
    # Shared device fingerprints
    dev_result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT d2.customer_id) AS shared_device_customers
            FROM devices d1
            JOIN devices d2
                ON d2.fingerprint = d1.fingerprint
                AND d2.customer_id != d1.customer_id
            WHERE d1.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    dev_row = dev_result.mappings().first() or {}

    # Shared IP addresses (30d)
    ip_result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT ih2.customer_id) AS shared_ip_customers
            FROM ip_history ih1
            JOIN ip_history ih2
                ON ih2.ip_address = ih1.ip_address
                AND ih2.customer_id != ih1.customer_id
            WHERE ih1.customer_id = :cid
              AND ih1.last_seen_at >= NOW() - INTERVAL '30 days'
              AND ih2.last_seen_at >= NOW() - INTERVAL '30 days'
        """),
        {"cid": customer_id},
    )
    ip_row = ip_result.mappings().first() or {}

    # Shared recipient accounts
    recip_result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT w2.customer_id) AS shared_recipient_customers
            FROM withdrawals w1
            JOIN withdrawals w2
                ON w2.recipient_account = w1.recipient_account
                AND w2.customer_id != w1.customer_id
            WHERE w1.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    recip_row = recip_result.mappings().first() or {}

    shared_device = int(dev_row.get("shared_device_customers", 0))
    shared_ip = int(ip_row.get("shared_ip_customers", 0))
    shared_recip = int(recip_row.get("shared_recipient_customers", 0))

    # Check if any connected customer is flagged
    flagged_result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT c.id) AS flagged_connections
            FROM customers c
            WHERE c.is_flagged = TRUE
              AND c.id != :cid
              AND c.id IN (
                  -- Shared device
                  SELECT d2.customer_id FROM devices d1
                  JOIN devices d2 ON d2.fingerprint = d1.fingerprint
                      AND d2.customer_id != d1.customer_id
                  WHERE d1.customer_id = :cid
                  UNION
                  -- Shared IP
                  SELECT ih2.customer_id FROM ip_history ih1
                  JOIN ip_history ih2 ON ih2.ip_address = ih1.ip_address
                      AND ih2.customer_id != ih1.customer_id
                  WHERE ih1.customer_id = :cid
                  UNION
                  -- Shared recipient
                  SELECT w2.customer_id FROM withdrawals w1
                  JOIN withdrawals w2 ON w2.recipient_account = w1.recipient_account
                      AND w2.customer_id != w1.customer_id
                  WHERE w1.customer_id = :cid
              )
        """),
        {"cid": customer_id},
    )
    flagged_row = flagged_result.mappings().first() or {}
    flagged_connections = int(flagged_row.get("flagged_connections", 0))

    # Second-degree exposure (evidence only): count customers connected
    # to this customer's direct connections
    second_result = await session.execute(
        text("""
            WITH direct_connections AS (
                SELECT DISTINCT d2.customer_id
                FROM devices d1
                JOIN devices d2 ON d2.fingerprint = d1.fingerprint
                    AND d2.customer_id != d1.customer_id
                WHERE d1.customer_id = :cid
                UNION
                SELECT DISTINCT ih2.customer_id
                FROM ip_history ih1
                JOIN ip_history ih2 ON ih2.ip_address = ih1.ip_address
                    AND ih2.customer_id != ih1.customer_id
                WHERE ih1.customer_id = :cid
            )
            SELECT COUNT(DISTINCT d4.customer_id) AS second_degree_count
            FROM direct_connections dc
            JOIN devices d3 ON d3.customer_id = dc.customer_id
            JOIN devices d4 ON d4.fingerprint = d3.fingerprint
                AND d4.customer_id != dc.customer_id
                AND d4.customer_id != :cid
        """),
        {"cid": customer_id},
    )
    second_row = second_result.mappings().first() or {}

    return {
        "shared_device_customers": shared_device,
        "shared_ip_customers": shared_ip,
        "shared_recipient_customers": shared_recip,
        "flagged_connections": flagged_connections,
        "second_degree_exposure": int(second_row.get("second_degree_count", 0)),
    }


def _compute_score(data: dict) -> tuple[float, dict, str]:
    """Score graph proximity from sub-signals."""
    shared_device = data["shared_device_customers"]
    shared_ip = data["shared_ip_customers"]
    shared_recip = data["shared_recipient_customers"]
    flagged = data["flagged_connections"]

    # Instant high score if connected to flagged customer
    if flagged > 0:
        score = 0.9
    else:
        device_score = _linear_score(shared_device, 0, 2)
        ip_score = _linear_score(shared_ip, 0, 3)
        recip_score = min(shared_recip, 1)  # Any shared recipient = 1.0

        score = round(
            (device_score * 0.35
             + ip_score * 0.30
             + recip_score * 0.35),
            4,
        )

    evidence = {
        "shared_device_customers": shared_device,
        "shared_ip_customers": shared_ip,
        "shared_recipient_customers": shared_recip,
        "flagged_connections": flagged,
        "second_degree_exposure": data["second_degree_exposure"],
        "detection_scope": "direct_entity_sharing_only",
    }

    reason = _build_reason(shared_device, shared_ip, shared_recip, flagged)

    return score, evidence, reason


def _build_reason(
    shared_device: int,
    shared_ip: int,
    shared_recip: int,
    flagged: int,
) -> str:
    """Build plain-English explanation."""
    parts: list[str] = []

    if flagged > 0:
        parts.append(
            f"Connected to {flagged} flagged customer(s) via shared entity"
        )

    if shared_device > 0:
        parts.append(
            f"Device fingerprint shared with {shared_device} other customer(s)"
        )

    if shared_ip > 0:
        parts.append(f"IP address shared with {shared_ip} other customer(s)")

    if shared_recip > 0:
        parts.append(
            f"Withdrawal recipient shared with {shared_recip} other customer(s)"
        )

    if not parts:
        return "No shared infrastructure detected"

    return "; ".join(parts)
