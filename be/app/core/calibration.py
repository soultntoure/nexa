"""Per-customer weight calibration — pure math, no DB or HTTP.

Tracks indicator precision (correct_fires / total_fires) per customer,
then adjusts indicator weights and blend ratios accordingly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.scoring import INDICATOR_WEIGHTS

# ── Constants ──
FIRE_THRESHOLD = 0.3
MIN_MULTIPLIER = 0.2
MAX_MULTIPLIER = 3.0
SENSITIVITY = 1.4
MIN_SAMPLE_SIZE = 3
WINDOW_SIZE = 20
DECAY_THRESHOLD_DAYS = 90
DECAY_RATE = 0.95

# Volatility controls (Bayesian smoothing)
PRIOR_STRENGTH = 2.0
PRIOR_CENTER = 0.5

# Event weighting (score strength + officer certainty)
BASE_EVENT_WEIGHT = 0.25
SCORE_STRENGTH_WEIGHT = 0.45
OFFICER_CERTAINTY_WEIGHT = 0.30

BLOCK_ACTIONS = {"blocked", "block"}
APPROVE_ACTIONS = {"approved", "approve"}

# Blend weight bounds
MIN_RULE_WEIGHT = 0.4
MAX_RULE_WEIGHT = 0.8
DEFAULT_RULE_WEIGHT = 0.5


def calculate_indicator_multiplier(
    correct_fires: float,
    total_fires: float,
    last_decision_date: datetime | None = None,
    sample_size: int | None = None,
) -> float:
    """Compute multiplier from precision. Returns 1.0 if insufficient data."""
    observed_fires = sample_size if sample_size is not None else int(round(total_fires))
    if observed_fires < MIN_SAMPLE_SIZE or total_fires <= 0:
        return 1.0
    precision = _smoothed_precision(correct_fires, total_fires)
    multiplier = 1.0 + (precision - 0.5) * SENSITIVITY
    multiplier = _clamp(multiplier, MIN_MULTIPLIER, MAX_MULTIPLIER)
    if last_decision_date is not None:
        multiplier = apply_decay(multiplier, last_decision_date)
    return round(multiplier, 4)


def apply_decay(multiplier: float, last_decision_date: datetime) -> float:
    """Drift multiplier toward 1.0 if no decisions in 90+ days."""
    now = datetime.now(timezone.utc)
    days_since = (now - last_decision_date).days
    if days_since <= DECAY_THRESHOLD_DAYS:
        return multiplier
    periods = (days_since - DECAY_THRESHOLD_DAYS) / 30.0
    decay_factor = DECAY_RATE ** periods
    return round(1.0 + (multiplier - 1.0) * decay_factor, 4)


def build_effective_weights(
    base_weights: dict[str, float],
    profile_weights: dict[str, dict[str, Any]] | None,
) -> dict[str, float]:
    """Merge base weights with per-customer multipliers."""
    if not profile_weights:
        return dict(base_weights)
    effective: dict[str, float] = {}
    for name, base in base_weights.items():
        entry = profile_weights.get(name)
        if entry and not entry.get("is_pinned", False):
            mult = _clamp(entry.get("multiplier", 1.0), MIN_MULTIPLIER, MAX_MULTIPLIER)
            effective[name] = base * mult
        elif entry and entry.get("is_pinned", False):
            effective[name] = base * entry.get("multiplier", 1.0)
        else:
            effective[name] = base
    return effective


def recalculate_profile(
    decisions: list[dict[str, Any]],
    current_profile: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Rebuild indicator_weights JSONB from a rolling decision window."""
    if current_profile is None:
        current_profile = {}
    stats = _count_indicator_stats(decisions)
    result: dict[str, dict[str, Any]] = {}
    for name in INDICATOR_WEIGHTS:
        stat = stats.get(name, _empty_stats())
        sample_size = int(stat["sample_size"])
        correct_fires = int(stat["correct_fires"])
        weighted_total = float(stat["weighted_total"])
        weighted_correct = float(stat["weighted_correct"])
        latest_decision_at = stat["latest_decision_at"]

        pinned = current_profile.get(name, {}).get("is_pinned", False)
        raw_precision = correct_fires / sample_size if sample_size > 0 else 0.0
        precision = _smoothed_precision(weighted_correct, weighted_total)
        multiplier = calculate_indicator_multiplier(
            weighted_correct,
            weighted_total,
            last_decision_date=latest_decision_at,
            sample_size=sample_size,
        )
        result[name] = {
            "multiplier": multiplier,
            "precision": round(precision, 4),
            "raw_precision": round(raw_precision, 4),
            "sample_size": sample_size,
            "correct_fires": correct_fires,
            "total_fires": sample_size,
            "weighted_correct_fires": round(weighted_correct, 4),
            "weighted_total_fires": round(weighted_total, 4),
            "is_pinned": pinned,
        }
    return result


def calculate_blend_weights(
    decisions: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute per-customer rule_engine/investigators blend ratio."""
    rule_correct = 0
    inv_correct = 0
    total = 0
    for d in decisions:
        inv_scores = d.get("investigator_scores")
        if not isinstance(inv_scores, dict) or not inv_scores:
            continue

        officer = str(d.get("officer_action", "")).strip().lower()
        if officer not in (BLOCK_ACTIONS | APPROVE_ACTIONS):
            continue

        numeric_scores = [
            _safe_float(score, default=-1.0)
            for score in inv_scores.values()
        ]
        numeric_scores = [score for score in numeric_scores if 0.0 <= score <= 1.0]
        if not numeric_scores:
            continue

        rule_decision = str(
            d.get("rule_decision") or d.get("evaluation_decision") or ""
        ).strip().lower()
        if not rule_decision:
            continue

        total += 1
        officer_blocked = officer in BLOCK_ACTIONS
        rule_blocked = rule_decision in BLOCK_ACTIONS
        inv_avg = sum(numeric_scores) / len(numeric_scores)
        inv_blocked = inv_avg >= 0.5

        if rule_blocked == officer_blocked:
            rule_correct += 1
        if inv_blocked == officer_blocked:
            inv_correct += 1
    if total == 0:
        return {"rule_engine": DEFAULT_RULE_WEIGHT, "investigators": 1.0 - DEFAULT_RULE_WEIGHT}
    rule_w = DEFAULT_RULE_WEIGHT + (rule_correct - inv_correct) / total * 0.2
    rule_w = _clamp(rule_w, MIN_RULE_WEIGHT, MAX_RULE_WEIGHT)
    return {"rule_engine": round(rule_w, 4), "investigators": round(1.0 - rule_w, 4)}


def _count_indicator_stats(
    decisions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Count weighted and raw fire stats per indicator from decision window."""
    stats: dict[str, dict[str, Any]] = {}
    for d in decisions:
        scores = d.get("indicator_scores", {})
        officer_action = str(d.get("officer_action", "")).strip().lower()
        officer_blocked = officer_action in BLOCK_ACTIONS
        officer_certainty = _estimate_officer_certainty(
            officer_action,
            d.get("composite_score"),
        )
        decision_dt = _parse_decision_time(d.get("decided_at"))
        for name, score in scores.items():
            score_value = _safe_float(score)
            if score_value < FIRE_THRESHOLD:
                continue

            if name not in stats:
                stats[name] = _empty_stats()

            weight = _event_weight(_score_strength(score_value), officer_certainty)
            stats[name]["sample_size"] += 1
            stats[name]["weighted_total"] += weight

            if officer_blocked:
                stats[name]["correct_fires"] += 1
                stats[name]["weighted_correct"] += weight

            latest = stats[name]["latest_decision_at"]
            if decision_dt and (latest is None or decision_dt > latest):
                stats[name]["latest_decision_at"] = decision_dt

    return stats


def _empty_stats() -> dict[str, Any]:
    return {
        "sample_size": 0,
        "correct_fires": 0,
        "weighted_total": 0.0,
        "weighted_correct": 0.0,
        "latest_decision_at": None,
    }


def _smoothed_precision(correct: float, total: float) -> float:
    if total <= 0:
        return PRIOR_CENTER
    numerator = correct + (PRIOR_CENTER * PRIOR_STRENGTH)
    denominator = total + PRIOR_STRENGTH
    return _clamp(numerator / denominator, 0.0, 1.0)


def _score_strength(score: float) -> float:
    if score <= FIRE_THRESHOLD:
        return 0.0
    span = 1.0 - FIRE_THRESHOLD
    return _clamp((score - FIRE_THRESHOLD) / span, 0.0, 1.0)


def _estimate_officer_certainty(officer_action: str, composite_score: Any) -> float:
    score = _clamp(_safe_float(composite_score, default=0.5), 0.0, 1.0)

    if officer_action in BLOCK_ACTIONS:
        return _clamp((score - 0.5) * 2.0, 0.0, 1.0)
    if officer_action in APPROVE_ACTIONS:
        return _clamp((0.5 - score) * 2.0, 0.0, 1.0)

    # Near-threshold choices (escalated/review) are treated as high-certainty mid-zone signals.
    return 1.0 - _clamp(abs(score - 0.5) * 2.0, 0.0, 1.0)


def _event_weight(score_strength: float, officer_certainty: float) -> float:
    weight = (
        BASE_EVENT_WEIGHT
        + (SCORE_STRENGTH_WEIGHT * _clamp(score_strength, 0.0, 1.0))
        + (OFFICER_CERTAINTY_WEIGHT * _clamp(officer_certainty, 0.0, 1.0))
    )
    return _clamp(weight, 0.1, 1.5)


def _parse_decision_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        text = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
