"""Pure math for weight drift analysis — no DB, no HTTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median, stdev


@dataclass
class OutlierResult:
    customer_id: str
    indicator_name: str
    multiplier: float
    deviation: float


@dataclass
class IndicatorStats:
    name: str
    mean: float
    median: float
    std: float
    min_val: float
    max_val: float
    trend: str
    outlier_count: int = 0


@dataclass
class DriftSummary:
    indicators: list[IndicatorStats] = field(default_factory=list)
    total_profiles: int = 0
    unique_customers: int = 0


def moving_average(values: list[float], window: int) -> list[float]:
    """Simple moving average over a list of floats."""
    if window <= 0 or not values:
        return []
    return [mean(values[max(0, i - window + 1):i + 1]) for i in range(len(values))]


def detect_outliers(values: list[tuple[str, str, float]]) -> list[OutlierResult]:
    """IQR-based outlier detection. Input: (customer_id, indicator, multiplier)."""
    if len(values) < 4:
        return []
    multipliers = [v[2] for v in values]
    sorted_m = sorted(multipliers)
    n = len(sorted_m)
    q1, q3 = sorted_m[n // 4], sorted_m[3 * n // 4]
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    med = median(multipliers)
    return [
        OutlierResult(cid, ind, m, round(abs(m - med), 4))
        for cid, ind, m in values if m < lower or m > upper
    ]


def build_drift_summary(profiles: list) -> DriftSummary:
    """Per-indicator stats from a list of weight profiles."""
    indicator_values: dict[str, list[float]] = {}
    customer_ids: set[str] = set()
    for p in profiles:
        customer_ids.add(str(getattr(p, "customer_id", "")))
        for name, entry in (getattr(p, "indicator_weights", {}) or {}).items():
            m = entry.get("multiplier", 1.0) if isinstance(entry, dict) else 1.0
            indicator_values.setdefault(name, []).append(m)

    stats = [
        IndicatorStats(
            name=name, mean=round(mean(v), 4), median=round(median(v), 4),
            std=round(stdev(v), 4) if len(v) > 1 else 0.0,
            min_val=round(min(v), 4), max_val=round(max(v), 4),
            trend=indicator_trend(v),
        )
        for name, v in indicator_values.items() if v
    ]
    return DriftSummary(indicators=stats, total_profiles=len(profiles), unique_customers=len(customer_ids))


def indicator_trend(series: list[float]) -> str:
    """'rising' / 'falling' / 'stable' via linear slope."""
    if len(series) < 2:
        return "stable"
    n = len(series)
    x_mean, y_mean = (n - 1) / 2, mean(series)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(series))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return "stable"
    slope = num / den
    return "rising" if slope > 0.05 else "falling" if slope < -0.05 else "stable"


def suggest_countermeasures(summary: DriftSummary) -> list[dict]:
    """Rule-based: flag indicators drifting >2.0 or <0.5."""
    results: list[dict] = []
    for ind in summary.indicators:
        if ind.max_val > 2.0:
            results.append({
                "indicator_name": ind.name,
                "issue": "This signal's influence grew unusually high for some customers",
                "suggestion": "Lock this signal's weight to prevent further drift",
                "severity": "high" if ind.max_val > 3.0 else "medium",
            })
        if ind.min_val < 0.5:
            results.append({
                "indicator_name": ind.name,
                "issue": "This signal is being underweighted and may miss real fraud",
                "suggestion": "Review whether this signal should carry more importance",
                "severity": "high" if ind.min_val < 0.2 else "medium",
            })
        if ind.std > 0.5:
            results.append({
                "indicator_name": ind.name,
                "issue": "This signal's weight varies a lot across customers",
                "suggestion": "Consider stabilizing this signal's weight range",
                "severity": "medium",
            })
    return results
