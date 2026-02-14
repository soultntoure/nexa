"""Pure candidate support metric calculations."""

from __future__ import annotations

from typing import Any


def avg_confidence(units: list[Any]) -> float:
    """Average confidence from cluster units (fallback 0.5)."""
    values = [unit.confidence for unit in units if unit.confidence is not None]
    return sum(values) / len(values) if values else 0.5


def evidence_quality(units: list[Any]) -> float:
    """Average evidence quality score from units (fallback 0.5)."""
    values = [unit.score for unit in units if unit.score is not None]
    return sum(values) / len(values) if values else 0.5


def novelty_to_float(status: str) -> float:
    """Map novelty status string to 0-1 score."""
    return {"new": 1.0, "similar": 0.5, "duplicate": 0.0}.get(status, 0.5)
