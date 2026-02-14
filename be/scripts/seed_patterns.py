"""
Run pattern detection against seed data and print found candidates.

Stub for now — will be wired to detection_service in Wave 2.

Run: python -m scripts.seed_patterns
Requires: running Postgres with seeded data (python -m scripts.seed_data)
"""

import asyncio
import uuid
from dataclasses import dataclass


# ── Deterministic UUID from name (same as seed_data.py) ──
def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"deriv.seed.{name}")


@dataclass
class PatternCandidate:
    """A detected fraud pattern candidate."""

    pattern_type: str
    customer_ids: list[uuid.UUID]
    confidence: float
    evidence: str


# ═══════════════════════════════════════════════════════════════════════════
# STUB DETECTORS — each checks one pattern type against seed data
# Will be replaced by detection_service calls in Wave 2.
# ═══════════════════════════════════════════════════════════════════════════


def _detect_no_trade_withdrawal() -> list[PatternCandidate]:
    """Detect no_trade_withdrawal: 0 trades + withdrawal > 90% of deposits."""
    return [
        PatternCandidate(
            pattern_type="no_trade_withdrawal",
            customer_ids=[_id("victor")],
            confidence=0.95,
            evidence="Victor Petrov: $3000 deposit, 0 trades, $2990 withdrawal (99.7%)",
        ),
    ]


def _detect_shared_device_ring() -> list[PatternCandidate]:
    """Detect shared_device_ring: 2+ customers sharing device fingerprint."""
    return [
        PatternCandidate(
            pattern_type="shared_device_ring",
            customer_ids=[_id("ahmed"), _id("fatima"), _id("chen_wei")],
            confidence=0.92,
            evidence=(
                "3 customers share device fingerprint deadbeef..., "
                "same IP 41.44.55.66, same recipient 'Mohamed Nour', "
                "withdrawals within 10 minutes of each other"
            ),
        ),
    ]


def _detect_card_testing() -> list[PatternCandidate]:
    """Detect card_testing_sequence: N failed deposits then success then withdrawal."""
    return [
        PatternCandidate(
            pattern_type="card_testing_sequence",
            customer_ids=[_id("sophie")],
            confidence=0.90,
            evidence=(
                "Sophie Laurent: 4 failed deposits (card_restricted) then 1 success, "
                "immediate $480 withdrawal (96% of $500 deposit)"
            ),
        ),
    ]


def _detect_velocity_burst() -> list[PatternCandidate]:
    """Detect velocity_burst: 4+ withdrawals within 1 hour."""
    return [
        PatternCandidate(
            pattern_type="velocity_burst",
            customer_ids=[_id("carlos")],
            confidence=0.94,
            evidence=(
                "Carlos Mendez: 5 withdrawals in 1 hour ($400 each = $2000), "
                "3 different devices, VPN IP"
            ),
        ),
    ]


def _detect_rapid_funding_cycle() -> list[PatternCandidate]:
    """Detect rapid_funding_cycle: 3+ deposit->withdrawal cycles within 6h each."""
    return [
        PatternCandidate(
            pattern_type="rapid_funding_cycle",
            customer_ids=[_id("nina")],
            confidence=0.88,
            evidence=(
                "Nina Volkov: 3 deposit->withdrawal cycles in 3 days, "
                "each cycle completes within ~4 hours ($800 in -> $750 out)"
            ),
        ),
    ]


DETECTORS = [
    _detect_no_trade_withdrawal,
    _detect_shared_device_ring,
    _detect_card_testing,
    _detect_velocity_burst,
    _detect_rapid_funding_cycle,
]

_CUSTOMER_NAMES = {
    str(_id("victor")): "Victor Petrov",
    str(_id("ahmed")): "Ahmed Hassan",
    str(_id("fatima")): "Fatima Nour",
    str(_id("chen_wei")): "Chen Wei",
    str(_id("sophie")): "Sophie Laurent",
    str(_id("carlos")): "Carlos Mendez",
    str(_id("nina")): "Nina Volkov",
}


async def run_detection() -> list[PatternCandidate]:
    """Run all stub detectors and return candidates.

    TODO (Wave 2): Replace stubs with detection_service.detect() calls
    that query the actual database.
    """
    candidates: list[PatternCandidate] = []
    for detector in DETECTORS:
        candidates.extend(detector())
    return candidates


async def main() -> None:
    print("=" * 70)
    print("SEED PATTERN DETECTION (stub)")
    print("=" * 70)
    print()

    candidates = await run_detection()

    for c in candidates:
        names = [
            _CUSTOMER_NAMES.get(str(cid), str(cid))
            for cid in c.customer_ids
        ]
        print(f"  [{c.pattern_type}]")
        print(f"    Customers:  {', '.join(names)}")
        print(f"    Confidence: {c.confidence:.0%}")
        print(f"    Evidence:   {c.evidence}")
        print()

    print(f"Total candidates found: {len(candidates)}")
    print()
    print("NOTE: These are stub results. Wire to detection_service in Wave 2.")


if __name__ == "__main__":
    asyncio.run(main())
