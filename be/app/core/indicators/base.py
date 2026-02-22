"""Indicator registry — IndicatorDef dataclass + INDICATORS list."""

import asyncio
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators._queries import (
    query_amount_anomaly,
    query_card_errors,
    query_device_fingerprint,
    query_geographic,
    query_payment_method,
    query_recipient,
    query_trading_behavior,
    query_velocity,
)
from app.core.indicators._scorers import (
    score_amount_anomaly,
    score_card_errors,
    score_device_fingerprint,
    score_geographic,
    score_payment_method,
    score_recipient,
    score_trading_behavior,
    score_velocity,
)


@dataclass(frozen=True)
class IndicatorDef:
    name: str
    weight: float
    query: Callable  # async (ctx, session) -> dict
    scorer: Callable  # pure  (evidence)  -> (float, str)


INDICATORS: list[IndicatorDef] = [
    IndicatorDef("velocity",           1.0, query_velocity,           score_velocity),
    IndicatorDef("amount_anomaly",     1.0, query_amount_anomaly,     score_amount_anomaly),
    IndicatorDef("payment_method",     1.0, query_payment_method,     score_payment_method),
    IndicatorDef("geographic",         1.0, query_geographic,         score_geographic),
    IndicatorDef("device_fingerprint", 1.3, query_device_fingerprint, score_device_fingerprint),
    IndicatorDef("trading_behavior",   1.5, query_trading_behavior,   score_trading_behavior),
    IndicatorDef("recipient",          1.0, query_recipient,          score_recipient),
    IndicatorDef("card_errors",        1.2, query_card_errors,        score_card_errors),
]


async def _run_one(
    defn: IndicatorDef,
    ctx: dict,
    session_factory: async_sessionmaker,
) -> IndicatorResult:
    async with session_factory() as session:
        evidence = await defn.query(ctx, session)
    score, reasoning = defn.scorer(evidence)
    return IndicatorResult(
        indicator_name=defn.name,
        score=score,
        confidence=1.0,
        reasoning=reasoning,
        evidence=evidence,
    )


async def run_all_indicators(
    ctx: dict, session_factory: async_sessionmaker,
) -> list[IndicatorResult]:
    """Run all indicators in parallel, each with its own session."""
    return list(await asyncio.gather(*[
        _run_one(defn, ctx, session_factory) for defn in INDICATORS
    ]))
