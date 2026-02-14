"""Velocity indicator — withdrawal frequency in time windows."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_system.schemas.indicators import IndicatorResult
from app.core.indicators.base import BaseIndicator
from app.data.db.repositories.withdrawal_repository import WithdrawalRepository


class VelocityIndicator(BaseIndicator):
    name = "velocity"
    weight = 1.0

    async def evaluate(
        self, ctx: dict, session: AsyncSession,
    ) -> IndicatorResult:
        repo = WithdrawalRepository(session)
        row = await repo.get_velocity_counts(ctx["customer_id"])

        c1h = int(row["count_1h"])
        c24h = int(row["count_24h"])
        c7d = int(row["count_7d"])
        c30d = int(row["count_30d"])

        score, reasoning, evidence = _compute_score(c1h, c24h, c7d, c30d)
        return IndicatorResult(
            indicator_name="velocity",
            score=score,
            confidence=1.0,
            reasoning=reasoning,
            evidence=evidence,
        )


def _compute_score(
    c1h: int, c24h: int, c7d: int, c30d: int,
) -> tuple[float, str, dict]:
    """Two-stage velocity scoring with customer baseline comparison."""
    baselines = _build_baselines(c24h, c30d)
    ratios = _build_spike_ratios(c1h, c24h, c7d, baselines)

    warn_threshold_hit = c1h >= 4 or c24h >= 7 or c7d >= 12
    critical_threshold_hit = c1h >= 6 or c24h >= 10 or c7d >= 18
    warn_spike_hit = any(value >= 2.5 for value in ratios.values())
    critical_spike_hit = any(value >= 4.0 for value in ratios.values())

    score = 0.0
    if warn_threshold_hit:
        score = 0.25
    if warn_threshold_hit and warn_spike_hit:
        score = max(score, 0.40)
    if critical_threshold_hit:
        score = max(score, 0.50)
    if critical_threshold_hit and critical_spike_hit:
        score = max(score, 0.65)

    evidence = {
        "count_1h": c1h,
        "count_24h": c24h,
        "count_7d": c7d,
        "count_30d": c30d,
        "baseline_1h": baselines["baseline_1h"],
        "baseline_24h": baselines["baseline_24h"],
        "baseline_7d": baselines["baseline_7d"],
        "spike_ratio_1h": ratios["spike_ratio_1h"],
        "spike_ratio_24h": ratios["spike_ratio_24h"],
        "spike_ratio_7d": ratios["spike_ratio_7d"],
        "warn_threshold_hit": warn_threshold_hit,
        "critical_threshold_hit": critical_threshold_hit,
        "warn_spike_hit": warn_spike_hit,
        "critical_spike_hit": critical_spike_hit,
    }

    score = min(score, 0.65)
    from app.core.indicators._reasoning import build_velocity_reasoning
    return score, build_velocity_reasoning(evidence, score), evidence


def _build_baselines(c24h: int, c30d: int) -> dict[str, float]:
    """Estimate customer-normal withdrawal cadence from recent history."""
    historical_29d = max(c30d - c24h, 0)
    baseline_24h = (
        historical_29d / 29.0 if historical_29d > 0 else c30d / 30.0
    )
    baseline_1h = baseline_24h / 24.0
    baseline_7d = baseline_24h * 7.0
    return {
        "baseline_1h": baseline_1h,
        "baseline_24h": baseline_24h,
        "baseline_7d": baseline_7d,
    }


def _build_spike_ratios(
    c1h: int, c24h: int, c7d: int, baselines: dict[str, float],
) -> dict[str, float]:
    """Compare active-window counts against customer baseline cadence."""
    baseline_1h = max(baselines["baseline_1h"], 0.5)
    baseline_24h = max(baselines["baseline_24h"], 1.5)
    baseline_7d = max(baselines["baseline_7d"], 3.0)

    return {
        "spike_ratio_1h": c1h / baseline_1h,
        "spike_ratio_24h": c24h / baseline_24h,
        "spike_ratio_7d": c7d / baseline_7d,
    }
