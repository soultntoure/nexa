"""
Posture signal registry and parallel runner.

Contains:
- ALL_SIGNALS: list of all signal classes
- run_all_signals(customer_id, session_factory) -> list[SignalResult]

Each signal runs with its own session (same pattern as core/indicators).
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.prefraud.signals.account_maturity import AccountMaturitySignal
from app.services.prefraud.signals.base import BaseSignal, SignalResult
from app.services.prefraud.signals.funding_behavior import FundingBehaviorSignal
from app.services.prefraud.signals.graph_proximity import GraphProximitySignal
from app.services.prefraud.signals.infrastructure_stability import (
    InfrastructureStabilitySignal,
)
from app.services.prefraud.signals.pattern_match import PatternMatchSignal
from app.services.prefraud.signals.payment_risk import PaymentRiskSignal
from app.services.prefraud.signals.velocity_trends import VelocityTrendsSignal

ALL_SIGNALS: list[type[BaseSignal]] = [
    AccountMaturitySignal,
    VelocityTrendsSignal,
    InfrastructureStabilitySignal,
    FundingBehaviorSignal,
    PaymentRiskSignal,
    GraphProximitySignal,
    PatternMatchSignal,
]


async def _run_one(
    cls: type[BaseSignal],
    customer_id: uuid.UUID,
    session_factory: async_sessionmaker,
) -> SignalResult:
    """Run a single signal with its own session."""
    async with session_factory() as session:
        return await cls().compute(customer_id, session)


async def run_all_signals(
    customer_id: uuid.UUID, session_factory: async_sessionmaker,
) -> list[SignalResult]:
    """Run all posture signals in parallel, each with its own session."""
    tasks = [
        _run_one(cls, customer_id, session_factory)
        for cls in ALL_SIGNALS
    ]
    return list(await asyncio.gather(*tasks))
