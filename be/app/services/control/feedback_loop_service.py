"""Feedback loop service — learns from officer decisions.

Runs two parallel loops when an officer submits a decision:
1. Pattern Recording — extracts fingerprint, saves to fraud_patterns
2. Weight Calibration — recalculates per-customer indicator weights

Fire-and-forget: called via asyncio.create_task, never blocks officer response.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.calibration import calculate_blend_weights, recalculate_profile
from app.core.pattern_fingerprint import extract_fingerprint
from app.data.db.models.customer_weight_profile import CustomerWeightProfile
from app.data.db.models.customer_fraud_signal import CustomerFraudSignal
from app.data.db.models.withdrawal import Withdrawal
from app.data.db.repositories.fraud_pattern_repository import CustomerFraudSignalRepository
from app.data.db.repositories.weight_profile_repository import WeightProfileRepository
from app.services.control.feedback_loop_helpers import (
    fetch_decision_history,
    fetch_indicator_results_for_evaluation,
)

logger = logging.getLogger(__name__)


class FeedbackLoopService:
    """Processes officer decisions into pattern records and weight calibration."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def process_decision(
        self,
        withdrawal_id: uuid.UUID,
        evaluation_id: uuid.UUID,
        officer_action: str,
    ) -> None:
        """Fire-and-forget orchestrator for both feedback loops."""
        try:
            customer_id = await self._get_customer_id(withdrawal_id)
            if customer_id is None:
                logger.warning("No customer found for withdrawal %s", withdrawal_id)
                return
            await asyncio.gather(
                self._record_pattern(evaluation_id, customer_id, officer_action),
                self._recalibrate_weights(customer_id),
            )
        except Exception:
            logger.exception(
                "Feedback loop failed: eval=%s withdrawal=%s action=%s",
                evaluation_id, withdrawal_id, officer_action,
            )

    async def _get_customer_id(self, withdrawal_id: uuid.UUID) -> uuid.UUID | None:
        """Fetch customer_id from the withdrawal record."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Withdrawal.customer_id).where(Withdrawal.id == withdrawal_id),
            )
            return result.scalar_one_or_none()

    async def _record_pattern(
        self, evaluation_id: uuid.UUID, customer_id: uuid.UUID, officer_action: str,
    ) -> None:
        """Loop 1: Extract fingerprint from indicator results, save to fraud_patterns."""
        async with self._session_factory() as session:
            results = await fetch_indicator_results_for_evaluation(session, evaluation_id)
            if not results:
                logger.warning("No indicator results for evaluation %s", evaluation_id)
                return
            fingerprint = extract_fingerprint(results, officer_action)
            if not fingerprint["indicator_combination"]:
                return
            repo = CustomerFraudSignalRepository(session)
            await _upsert_pattern(repo, fingerprint, customer_id, evaluation_id)

    async def _recalibrate_weights(self, customer_id: uuid.UUID) -> None:
        """Loop 2: Fetch decision history, recalculate weights, save profile."""
        async with self._session_factory() as session:
            decisions = await fetch_decision_history(session, customer_id)
            if not decisions:
                logger.info("No decision history for customer %s", customer_id)
                return
            current = await _load_current_profile(session, customer_id)
            new_weights = recalculate_profile(decisions, current)
            new_blend = calculate_blend_weights(decisions)
            profile = CustomerWeightProfile(
                customer_id=customer_id,
                indicator_weights=new_weights,
                blend_weights=new_blend,
                decision_window=decisions,
            )
            repo = WeightProfileRepository(session)
            await repo.save_profile(profile)


async def _upsert_pattern(
    repo: CustomerFraudSignalRepository,
    fingerprint: dict,
    customer_id: uuid.UUID,
    evaluation_id: uuid.UUID,
) -> None:
    """Insert new pattern or increment frequency on existing match."""
    combo = fingerprint["indicator_combination"]
    signal = fingerprint["signal_type"]
    existing = await repo.find_matching_pattern(combo, signal)
    if existing:
        await repo.increment_frequency(existing.id)
        return
    pattern = CustomerFraudSignal(
        pattern_type=f"{signal}_{fingerprint['score_band']}",
        description=f"Officer-confirmed {signal}: {', '.join(combo)}",
        indicator_combination=combo,
        signal_type=signal,
        indicator_scores=fingerprint["indicator_scores"],
        customer_id=customer_id,
        evaluation_id=evaluation_id,
        frequency=1,
        confidence=1.0,
    )
    await repo.create(pattern)


async def _load_current_profile(
    session, customer_id: uuid.UUID,
) -> dict | None:
    """Load active weight profile's indicator_weights, or None."""
    repo = WeightProfileRepository(session)
    profile = await repo.get_active(customer_id)
    return profile.indicator_weights if profile else None
