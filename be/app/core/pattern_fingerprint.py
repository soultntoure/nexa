"""Pattern fingerprint extraction — pure functions, no DB or HTTP.

Extracts a canonical fingerprint from indicator results + officer action,
used to record confirmed fraud or false positive patterns.
"""

from __future__ import annotations

from typing import Any

FIRE_THRESHOLD = 0.3


def extract_fingerprint(
    indicator_results: list[dict[str, Any]],
    officer_action: str,
) -> dict[str, Any]:
    """Build full fingerprint dict from indicator results and officer action."""
    fired = [r for r in indicator_results if r.get("score", 0) >= FIRE_THRESHOLD]
    combination = build_indicator_combination(fired)
    scores = _build_indicator_scores(fired)
    signal = "confirmed_fraud" if officer_action == "blocked" else "false_positive"
    composite = sum(r.get("score", 0) for r in fired) / max(len(fired), 1)
    return {
        "indicator_combination": combination,
        "indicator_scores": scores,
        "signal_type": signal,
        "score_band": classify_score_band(composite),
    }


def build_indicator_combination(
    fired_results: list[dict[str, Any]],
) -> list[str]:
    """Sorted list of indicator names that fired."""
    return sorted(r.get("indicator_name", "") for r in fired_results)


def classify_score_band(score: float) -> str:
    """Map a score to low/medium/high band."""
    if score < 0.30:
        return "low"
    if score < 0.70:
        return "medium"
    return "high"


def extract_evidence_keys(evidence: dict[str, Any] | None) -> list[str]:
    """Get sorted top-level keys from an evidence dict."""
    if not evidence:
        return []
    return sorted(evidence.keys())


def _build_indicator_scores(
    fired_results: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build the indicator_scores JSONB payload from fired indicators."""
    scores: dict[str, dict[str, Any]] = {}
    for r in fired_results:
        name = r.get("indicator_name", "")
        scores[name] = {
            "score": r.get("score", 0),
            "confidence": r.get("confidence", 0),
            "evidence_keys": extract_evidence_keys(r.get("evidence")),
        }
    return scores
