"""
Seed posture history + validation — generate trajectories and verify results.

1. Seeds 6 historical posture snapshots per customer (trajectory analysis)
2. Runs PostureService.recompute_all() to set current snapshots
3. Validates that each customer lands in the expected posture tier

  Clean   (6 customers) -> normal     (composite < 0.30)
  Escalate(4 customers) -> watch      (0.30 <= composite < 0.60)
  Fraud   (5 customers) -> high_risk  (composite >= 0.60)

Carlos (CUST-015) and Nina (CUST-016) accept watch OR high_risk since their
enrichments are profile-dependent and the spec marks them as TBD.

Run:      python -m scripts.seed_postures
Requires: running Postgres with seeded data (python -m scripts.seed_data)
"""

import asyncio
import time
import uuid

from app.data.db.engine import AsyncSessionLocal
from app.services.prefraud.posture_service import PostureService

# ── Deterministic UUID matching seed_data.py ──


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"deriv.seed.{name}")


# ── Expected outcomes from spec ──

EXPECTATIONS: list[tuple[str, str, uuid.UUID, list[str]]] = [
    # (external_id, name, customer_uuid, acceptable_postures)
    # Clean — normal
    ("CUST-001", "Sarah Chen", _id("sarah"), ["normal"]),
    ("CUST-002", "James Wilson", _id("james"), ["normal"]),
    ("CUST-003", "Aisha Mohammed", _id("aisha"), ["normal"]),
    ("CUST-004", "Kenji Sato", _id("kenji"), ["normal"]),
    ("CUST-005", "Emma Davies", _id("emma"), ["normal"]),
    ("CUST-006", "Raj Patel", _id("raj"), ["normal"]),
    # Escalate — watch
    ("CUST-007", "David Park", _id("david"), ["watch"]),
    ("CUST-008", "Maria Santos", _id("maria"), ["watch"]),
    ("CUST-009", "Tom Brown", _id("tom"), ["watch"]),
    ("CUST-010", "Yuki Tanaka", _id("yuki"), ["watch"]),
    # Fraud — high_risk (Carlos and Nina accept watch or high_risk)
    ("CUST-011", "Victor Petrov", _id("victor"), ["high_risk"]),
    ("CUST-012", "Sophie Laurent", _id("sophie"), ["high_risk"]),
    ("CUST-013", "Ahmed Hassan", _id("ahmed"), ["high_risk"]),
    ("CUST-014", "Fatima Nour", _id("fatima"), ["high_risk"]),
    ("CUST-015", "Carlos Mendez", _id("carlos"), ["watch", "high_risk"]),
    ("CUST-016", "Nina Volkov", _id("nina"), ["watch", "high_risk"]),
]

# ── Display helpers ──

POSTURE_ICONS = {"normal": "  ", "watch": "! ", "high_risk": "!!"}
TIER_LABELS = {
    "normal": "CLEAN",
    "watch": "ESCALATE",
    "high_risk": "FRAUD",
}


def _bar(score: float, width: int = 20) -> str:
    """ASCII bar chart for a 0.0-1.0 score."""
    filled = int(round(score * width))
    return f"[{'#' * filled}{'.' * (width - filled)}] {score:.4f}"


def _print_customer(
    ext_id: str,
    name: str,
    posture: str,
    composite: float,
    signal_scores: dict[str, float],
    top_reasons: list[str],
    passed: bool,
    expected: list[str],
) -> None:
    """Print formatted output for one customer."""
    status = "PASS" if passed else "FAIL"
    icon = POSTURE_ICONS.get(posture, "  ")
    tier = TIER_LABELS.get(posture, posture.upper())

    print(f"\n{'=' * 70}")
    print(f"  {icon}{ext_id}  {name:<20s}  [{status}]")
    print(f"  Posture: {posture} ({tier})   Composite: {composite:.4f}")
    if not passed:
        print(f"  ** EXPECTED: {' or '.join(expected)} **")
    print(f"  {'-' * 60}")

    # Signal breakdown
    for sig_name, sig_score in sorted(
        signal_scores.items(), key=lambda x: x[1], reverse=True,
    ):
        print(f"    {sig_name:<30s} {_bar(sig_score)}")

    # Top reasons
    if top_reasons:
        print(f"  {'-' * 60}")
        print("  Top reasons:")
        for reason in top_reasons:
            print(f"    - {reason}")


def _print_summary(
    results: dict[str, int],
    total: int,
    passed: int,
    failed: int,
    elapsed: float,
) -> None:
    """Print final summary."""
    print(f"\n{'=' * 70}")
    print("  POSTURE VALIDATION SUMMARY")
    print(f"  {'-' * 60}")
    print(f"  Customers computed:  {total}")
    print(f"  normal:              {results.get('normal', 0)}")
    print(f"  watch:               {results.get('watch', 0)}")
    print(f"  high_risk:           {results.get('high_risk', 0)}")
    print(f"  {'-' * 60}")
    print(f"  Passed:  {passed}/{total}")
    print(f"  Failed:  {failed}/{total}")
    print(f"  Elapsed: {elapsed:.2f}s")
    print(f"{'=' * 70}")

    if failed > 0:
        print("\n  Some customers did not land in the expected posture tier.")
        print("  Review signal scores above and adjust seed enrichments if needed.")
    else:
        print("\n  All customers matched expected posture tiers.")


# ── Main ──


async def main() -> None:
    """Seed posture history, recompute all, and validate against expectations."""
    from scripts.seed_posture_history import seed_posture_history

    service = PostureService(AsyncSessionLocal)

    # Step 1: Seed historical snapshots for trajectory analysis
    print(f"{'=' * 70}")
    print("  SEED POSTURE HISTORY + VALIDATION")
    print(f"{'=' * 70}")

    async with AsyncSessionLocal() as session:
        count = await seed_posture_history(session)
        await session.commit()
    print(f"  Seeded {count} historical posture snapshots.")

    # Step 2: Recompute current postures (overwrites is_current)
    print(f"  Recomputing postures for {len(EXPECTATIONS)} customers...")
    start = time.perf_counter()
    snapshots = await service.recompute_all(trigger="validation")
    elapsed = time.perf_counter() - start

    # Index snapshots by customer_id for lookup
    snapshot_map = {s.customer_id: s for s in snapshots}

    passed = 0
    failed = 0
    posture_counts: dict[str, int] = {}

    for ext_id, name, cid, expected_postures in EXPECTATIONS:
        snapshot = snapshot_map.get(cid)

        if snapshot is None:
            print(f"\n  FAIL: {ext_id} {name} -- no posture computed")
            failed += 1
            continue

        posture = snapshot.posture
        composite = snapshot.composite_score
        signal_scores = snapshot.signal_scores or {}
        evidence = snapshot.signal_evidence or {}
        top_reasons = evidence.get("top_reasons", [])

        is_pass = posture in expected_postures
        if is_pass:
            passed += 1
        else:
            failed += 1

        posture_counts[posture] = posture_counts.get(posture, 0) + 1

        _print_customer(
            ext_id, name, posture, composite,
            signal_scores, top_reasons,
            is_pass, expected_postures,
        )

    _print_summary(posture_counts, len(EXPECTATIONS), passed, failed, elapsed)


if __name__ == "__main__":
    asyncio.run(main())
