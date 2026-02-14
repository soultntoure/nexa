"""
Posture service — orchestrates signal computation and snapshot persistence.

Contains:
- PostureService class (takes async_sessionmaker)
  - recompute(customer_id, trigger) -> CustomerRiskPosture
  - get_current(customer_id) -> CustomerRiskPosture | None
  - recompute_all(trigger) -> list[CustomerRiskPosture]

Responsibilities:
1. Runs all 6 signals in parallel via run_all_signals()
2. Computes composite score and maps to posture state
3. Builds signal_scores + signal_evidence JSONB structures
4. Persists snapshot via PostureRepository.save_snapshot()
5. Implements debounce (skip if last compute < POSTURE_DEBOUNCE_S ago)

Follows InvestigatorService pattern: session_factory in __init__,
each operation opens its own session.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.data.db.models.customer import Customer
from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.data.db.repositories.posture_repository import PostureRepository
from app.services.prefraud.signals import run_all_signals
from app.services.prefraud.signals.base import (
    SignalResult,
    compute_composite,
    map_posture,
)

logger = logging.getLogger(__name__)


def _build_signal_scores(results: list[SignalResult]) -> dict[str, float]:
    """Build the signal_scores JSONB from signal results."""
    return {r.name: round(r.score, 4) for r in results}


def _build_signal_evidence(results: list[SignalResult]) -> dict:
    """Build the signal_evidence JSONB with top_reasons + per-signal detail.

    Structure matches the spec:
    {
        "top_reasons": [...],
        "signals": { "signal_name": { ...evidence, "reason": "..." }, ... }
    }
    """
    signals: dict = {}
    scored_reasons: list[tuple[float, str]] = []

    for r in results:
        signals[r.name] = {**r.evidence, "reason": r.reason}
        if r.score > 0.0 and r.reason:
            scored_reasons.append((r.score, r.reason))

    # Top reasons: highest-scoring signals first, max 3
    scored_reasons.sort(key=lambda x: x[0], reverse=True)
    top_reasons = [reason for _, reason in scored_reasons[:3]]

    return {"top_reasons": top_reasons, "signals": signals}


def _seconds_since(dt: datetime) -> float:
    """Seconds elapsed since a timezone-aware datetime."""
    return (datetime.now(timezone.utc) - dt).total_seconds()


class PostureService:
    """Orchestrates posture computation, persistence, and retrieval."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def recompute(
        self,
        customer_id: uuid.UUID,
        trigger: str = "manual",
    ) -> CustomerRiskPosture:
        """Compute posture for a customer and persist the snapshot.

        Args:
            customer_id: UUID of the customer to evaluate
            trigger: Source of the recompute ('scheduled', 'manual',
                     'event:new_device', etc.)

        Returns:
            Newly created CustomerRiskPosture (detached)
        """
        settings = get_settings()

        # Debounce: skip if last compute was recent
        async with self._session_factory() as session:
            repo = PostureRepository(session)
            current = await repo.get_current(customer_id)

        if current and _seconds_since(current.computed_at) < settings.POSTURE_DEBOUNCE_S:
            logger.debug(
                "Debounce: skipping recompute for %s (last=%ss ago)",
                customer_id,
                round(_seconds_since(current.computed_at), 1),
            )
            return current

        # Run all signals in parallel
        results = await run_all_signals(customer_id, self._session_factory)

        # Compute composite + posture state
        composite = round(compute_composite(results), 4)
        posture_state = map_posture(composite)

        # Build JSONB payloads
        signal_scores = _build_signal_scores(results)
        signal_evidence = _build_signal_evidence(results)

        # Create and persist snapshot
        snapshot = CustomerRiskPosture(
            customer_id=customer_id,
            posture=posture_state,
            composite_score=composite,
            signal_scores=signal_scores,
            signal_evidence=signal_evidence,
            trigger=trigger,
        )

        async with self._session_factory() as session:
            repo = PostureRepository(session)
            saved = await repo.save_snapshot(snapshot)

        logger.info(
            "Posture computed: customer=%s posture=%s score=%.4f trigger=%s",
            customer_id, posture_state, composite, trigger,
        )
        return saved

    async def get_current(self, customer_id: uuid.UUID) -> CustomerRiskPosture | None:
        """Get the current posture for a customer.

        Returns:
            Detached CustomerRiskPosture if exists, None otherwise
        """
        async with self._session_factory() as session:
            repo = PostureRepository(session)
            return await repo.get_current(customer_id)

    async def recompute_all(
        self, trigger: str = "scheduled",
    ) -> list[CustomerRiskPosture]:
        """Recompute posture for all active customers.

        Iterates all customers and runs recompute() for each.
        Failures for individual customers are logged and skipped.

        Args:
            trigger: Source of the bulk recompute

        Returns:
            List of successfully computed posture snapshots
        """
        async with self._session_factory() as session:
            result = await session.execute(select(Customer.id))
            customer_ids = list(result.scalars().all())

        logger.info(
            "Bulk recompute started: %d customers, trigger=%s",
            len(customer_ids), trigger,
        )

        snapshots: list[CustomerRiskPosture] = []
        for cid in customer_ids:
            try:
                snapshot = await self.recompute(cid, trigger=trigger)
                snapshots.append(snapshot)
            except Exception:
                logger.exception("Failed to recompute posture for %s", cid)

        logger.info(
            "Bulk recompute finished: %d/%d succeeded",
            len(snapshots), len(customer_ids),
        )
        return snapshots
