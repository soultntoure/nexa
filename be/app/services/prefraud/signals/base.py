"""
Signal framework — base class, result dataclass, and posture constants.

Contains:
- SignalResult: frozen dataclass returned by every signal
- BaseSignal: abstract base for all posture signal implementations
- Posture constants: weights, thresholds, uplift cap
- _linear_score: helper for sub-signal interpolation

Every signal receives a customer_id + AsyncSession and returns a SignalResult.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


# ── Result dataclass ──

@dataclass(frozen=True)
class SignalResult:
    """Output of a single posture signal computation."""

    name: str
    score: float  # 0.0 (safe) to 1.0 (risky)
    evidence: dict[str, Any]
    reason: str


# ── Abstract base ──

class BaseSignal(ABC):
    """Base class for posture signal implementations."""

    name: str

    @abstractmethod
    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        """Compute signal score for a customer."""


# ── Posture constants ──

POSTURE_SIGNAL_WEIGHTS: dict[str, float] = {
    "account_maturity": 1.0,
    "velocity_trends": 1.2,
    "infrastructure_stability": 1.3,
    "funding_behavior": 1.5,
    "payment_risk": 1.1,
    "graph_proximity": 1.4,
    "pattern_match": 1.4,
}

POSTURE_GLOBAL_MULTIPLIER: float = 1.0

POSTURE_THRESHOLDS: dict[str, float] = {
    "normal_below": 0.30,
    "watch_below": 0.60,
}

MAX_POSTURE_UPLIFT: float = 0.15
POSTURE_UPLIFT_WEIGHT: float = 0.3


# ── Scoring helpers ──

def _linear_score(value: float, safe: float, risky: float) -> float:
    """Linear interpolation: 0.0 at safe boundary, 1.0 at risky boundary.

    Handles both directions (safe < risky and safe > risky).
    Result is clamped to [0.0, 1.0].
    """
    if safe == risky:
        return 0.0
    normalized = (value - safe) / (risky - safe)
    return max(0.0, min(1.0, normalized))


def compute_composite(signal_results: list[SignalResult]) -> float:
    """Weighted average of signal scores, matching scoring.py pattern.

    composite = GLOBAL_MULTIPLIER * sum(score * weight) / sum(weight)
    """
    total_weighted = 0.0
    total_weight = 0.0

    for result in signal_results:
        weight = POSTURE_SIGNAL_WEIGHTS.get(result.name, 1.0)
        total_weighted += result.score * weight
        total_weight += weight

    if total_weight == 0.0:
        return 0.0

    return POSTURE_GLOBAL_MULTIPLIER * total_weighted / total_weight


def map_posture(composite: float) -> str:
    """Map composite score to posture state."""
    if composite < POSTURE_THRESHOLDS["normal_below"]:
        return "normal"
    if composite < POSTURE_THRESHOLDS["watch_below"]:
        return "watch"
    return "high_risk"
