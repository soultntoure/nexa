"""Statistical analysis tools — @tool functions for agents alongside SQL tools.

Agents fetch raw data via sql_db_query, then pass results here for computation.
"""

import statistics
from datetime import datetime, timezone

from langchain_core.tools import tool


@tool
def calculate_statistics(values: list[float]) -> dict:
    """Calculate descriptive statistics for a list of numeric values.

    Returns mean, std_dev, median, p25, p75, min, max, count.
    """
    if not values:
        return {"error": "Empty values list"}

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mean = statistics.mean(sorted_vals)
    std_dev = statistics.stdev(sorted_vals) if n > 1 else 0.0
    quantiles = statistics.quantiles(sorted_vals, n=4) if n >= 4 else []

    return {
        "mean": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "median": round(statistics.median(sorted_vals), 4),
        "p25": round(quantiles[0], 4) if quantiles else None,
        "p75": round(quantiles[2], 4) if quantiles else None,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
        "count": n,
    }


@tool
def detect_anomaly(
    value: float, history: list[float], threshold: float = 2.0
) -> dict:
    """Detect if a value is anomalous compared to historical data.

    Uses z-score. Returns z_score, is_anomaly, percentile, deviation_pct.
    """
    if len(history) < 2:
        return {"error": "Need at least 2 historical values"}

    mean = statistics.mean(history)
    std_dev = statistics.stdev(history)

    if std_dev == 0:
        return {
            "z_score": 0.0,
            "is_anomaly": value != mean,
            "percentile": 50.0,
            "deviation_pct": 0.0,
        }

    z_score = (value - mean) / std_dev
    below_count = sum(1 for v in history if v <= value)
    percentile = (below_count / len(history)) * 100
    deviation_pct = ((value - mean) / mean) * 100 if mean != 0 else 0.0

    return {
        "z_score": round(z_score, 4),
        "is_anomaly": abs(z_score) > threshold,
        "percentile": round(percentile, 2),
        "deviation_pct": round(deviation_pct, 2),
    }


@tool
def calculate_velocity(
    timestamps: list[str], windows: list[int] | None = None
) -> dict:
    """Count events per time window from ISO timestamps.

    Args:
        timestamps: ISO-format datetime strings.
        windows: Hours for each window (default [1, 24, 168]).

    Returns dict mapping window_hours to event count.
    """
    if windows is None:
        windows = [1, 24, 168]

    if not timestamps:
        return {str(w): 0 for w in windows}

    now = datetime.now(timezone.utc)
    parsed = []
    for ts in timestamps:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        parsed.append(dt)

    result: dict[str, int] = {}
    for window_hours in windows:
        cutoff = now.timestamp() - (window_hours * 3600)
        count = sum(1 for dt in parsed if dt.timestamp() >= cutoff)
        result[str(window_hours)] = count

    return result


@tool
def compare_to_cohort(value: float, cohort_values: list[float]) -> dict:
    """Compare a value against a cohort distribution.

    Returns percentile_rank, above_mean, std_devs_from_mean.
    """
    if not cohort_values:
        return {"error": "Empty cohort"}

    mean = statistics.mean(cohort_values)
    std_dev = statistics.stdev(cohort_values) if len(cohort_values) > 1 else 0.0
    below_count = sum(1 for v in cohort_values if v <= value)
    percentile_rank = (below_count / len(cohort_values)) * 100

    std_devs = (value - mean) / std_dev if std_dev > 0 else 0.0

    return {
        "percentile_rank": round(percentile_rank, 2),
        "above_mean": value > mean,
        "std_devs_from_mean": round(std_devs, 4),
    }
