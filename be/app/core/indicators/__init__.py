"""Rule-based indicator registry and parallel runner."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.amount_anomaly import AmountAnomalyIndicator
from app.core.indicators.base import BaseIndicator
from app.core.indicators.card_errors import CardErrorsIndicator
from app.core.indicators.device_fingerprint import DeviceFingerprintIndicator
from app.core.indicators.geographic import GeographicIndicator
from app.core.indicators.payment_method import PaymentMethodIndicator
from app.core.indicators.recipient import RecipientIndicator
from app.core.indicators.trading_behavior import TradingBehaviorIndicator
from app.core.indicators.velocity import VelocityIndicator

ALL_INDICATORS: list[type[BaseIndicator]] = [
    AmountAnomalyIndicator,
    VelocityIndicator,
    PaymentMethodIndicator,
    GeographicIndicator,
    DeviceFingerprintIndicator,
    TradingBehaviorIndicator,
    RecipientIndicator,
    CardErrorsIndicator,
]


async def _run_one(
    cls: type[BaseIndicator],
    ctx: dict,
    session_factory: async_sessionmaker,
) -> IndicatorResult:
    """Run a single indicator with its own session."""
    async with session_factory() as session:
        return await cls().evaluate(ctx, session)


async def run_all_indicators(
    ctx: dict, session_factory: async_sessionmaker,
) -> list[IndicatorResult]:
    """Run all 8 indicators in parallel, each with its own session."""
    tasks = [
        _run_one(cls, ctx, session_factory)
        for cls in ALL_INDICATORS
    ]
    return list(await asyncio.gather(*tasks))
