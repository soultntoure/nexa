"""
Infrastructure Stability signal — detects device churn, IP instability, VPN usage.

Sub-signals:
- Device count (30d): 1 safe, >= 4 risky
- Newest device age: >= 30d safe, <= 1d risky
- Has trusted device: yes safe, no risky
- Distinct IPs (30d): <= 2 safe, >= 8 risky
- Distinct countries (30d): 1 safe, >= 4 risky
- VPN usage ratio (30d): 0% safe, >= 50% risky

Inputs: devices, ip_history
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prefraud.signals.base import BaseSignal, SignalResult, _linear_score


class InfrastructureStabilitySignal(BaseSignal):
    """Scores device and network infrastructure stability."""

    name = "infrastructure_stability"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        data = await _fetch_infra_data(customer_id, session)
        score, evidence, reason = _compute_score(data)
        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )


async def _fetch_infra_data(
    customer_id: uuid.UUID, session: AsyncSession,
) -> dict:
    """Fetch device and IP statistics for the customer."""
    # Device stats
    dev_result = await session.execute(
        text("""
            SELECT
                COUNT(*) FILTER (
                    WHERE d.first_seen_at >= NOW() - INTERVAL '30 days'
                        OR d.last_seen_at >= NOW() - INTERVAL '30 days'
                ) AS device_count_30d,
                MIN(
                    EXTRACT(EPOCH FROM (NOW() - d.first_seen_at)) / 86400.0
                ) AS newest_device_age_days,
                BOOL_OR(d.is_trusted) AS has_trusted_device
            FROM devices d
            WHERE d.customer_id = :cid
        """),
        {"cid": customer_id},
    )
    dev_row = dev_result.mappings().first() or {}

    # IP stats
    ip_result = await session.execute(
        text("""
            SELECT
                COUNT(DISTINCT ih.ip_address) AS distinct_ips_30d,
                COUNT(DISTINCT
                    CASE WHEN ih.location IS NOT NULL
                        THEN SPLIT_PART(ih.location, ', ', 2)
                    END
                ) AS distinct_countries_30d,
                CASE
                    WHEN COUNT(*) = 0 THEN 0
                    ELSE COUNT(*) FILTER (WHERE ih.is_vpn = TRUE)::FLOAT
                         / COUNT(*)::FLOAT
                END AS vpn_usage_ratio
            FROM ip_history ih
            WHERE ih.customer_id = :cid
              AND ih.last_seen_at >= NOW() - INTERVAL '30 days'
        """),
        {"cid": customer_id},
    )
    ip_row = ip_result.mappings().first() or {}

    return {
        "device_count_30d": int(dev_row.get("device_count_30d", 0)),
        "newest_device_age_days": float(dev_row.get("newest_device_age_days", 0) or 0),
        "has_trusted_device": bool(dev_row.get("has_trusted_device", False)),
        "distinct_ips_30d": int(ip_row.get("distinct_ips_30d", 0)),
        "distinct_countries_30d": int(ip_row.get("distinct_countries_30d", 0)),
        "vpn_usage_ratio": float(ip_row.get("vpn_usage_ratio", 0)),
    }


def _compute_score(data: dict) -> tuple[float, dict, str]:
    """Score infrastructure stability from sub-signals."""
    device_count = data["device_count_30d"]
    newest_age = data["newest_device_age_days"]
    has_trusted = data["has_trusted_device"]
    distinct_ips = data["distinct_ips_30d"]
    distinct_countries = data["distinct_countries_30d"]
    vpn_ratio = data["vpn_usage_ratio"]

    # Sub-signal scores
    device_count_score = _linear_score(device_count, 1, 4)
    newest_age_score = _linear_score(newest_age, 30.0, 1.0)
    trusted_score = 0.0 if has_trusted else 1.0
    ip_score = _linear_score(distinct_ips, 2, 8)
    country_score = _linear_score(distinct_countries, 1, 4)
    vpn_score = _linear_score(vpn_ratio, 0.0, 0.5)

    # Weighted average
    score = round(
        (device_count_score * 0.15
         + newest_age_score * 0.15
         + trusted_score * 0.15
         + ip_score * 0.20
         + country_score * 0.20
         + vpn_score * 0.15),
        4,
    )

    evidence = {
        "device_count_30d": device_count,
        "newest_device_age_days": round(newest_age, 1),
        "has_trusted_device": has_trusted,
        "distinct_ips_30d": distinct_ips,
        "distinct_countries_30d": distinct_countries,
        "vpn_usage_ratio": round(vpn_ratio, 2),
    }

    reason = _build_reason(
        device_count, newest_age, has_trusted,
        distinct_ips, distinct_countries, vpn_ratio,
    )

    return score, evidence, reason


def _build_reason(
    device_count: int,
    newest_age: float,
    has_trusted: bool,
    distinct_ips: int,
    distinct_countries: int,
    vpn_ratio: float,
) -> str:
    """Build plain-English explanation."""
    parts: list[str] = []

    if device_count >= 4:
        parts.append(f"{device_count} devices seen in 30d (high churn)")
    elif device_count >= 3:
        parts.append(f"{device_count} devices in 30d")

    if newest_age <= 1:
        parts.append("Brand-new device detected")
    elif newest_age <= 7:
        parts.append(f"Newest device is {newest_age:.0f} days old")

    if not has_trusted and device_count > 0:
        parts.append("No trusted device")

    if distinct_countries >= 4:
        parts.append(f"{distinct_countries} countries in 30d")
    elif distinct_countries >= 2:
        parts.append(f"{distinct_countries} countries in 30d")

    if vpn_ratio >= 0.5:
        parts.append(f"VPN usage at {vpn_ratio:.0%}")
    elif vpn_ratio > 0:
        parts.append(f"Some VPN usage ({vpn_ratio:.0%})")

    if distinct_ips >= 8:
        parts.append(f"{distinct_ips} distinct IPs in 30d")

    if not parts:
        return "Stable infrastructure — single device, consistent IP"

    return "; ".join(parts)
