"""Build prompt sections describing per-customer weight adjustments."""

from typing import Any

DAMPENED_THRESHOLD = 0.85
BOOSTED_THRESHOLD = 1.15
WATCHLIST_DELTA = 0.08
MIN_SAMPLE_DISPLAY = 2
DEFAULT_RULE_WEIGHT = 0.5
DEFAULT_INVESTIGATOR_WEIGHT = 0.5

INVESTIGATOR_INDICATORS: dict[str, list[str]] = {
    "financial_behavior": [
        "amount_anomaly", "velocity", "trading_behavior", "payment_method",
    ],
    "identity_access": ["geographic", "device_fingerprint"],
    "cross_account": ["recipient", "card_errors", "device_fingerprint"],
}


def build_weight_context(
    indicator_weights: dict[str, Any] | None,
    blend_weights: dict[str, float] | None,
    relevant_indicators: list[str] | None = None,
) -> str:
    """Build a prompt section describing per-customer weight adjustments.

    Returns empty string if no profile exists (new customer).
    """
    if not indicator_weights:
        return ""

    dampened = _classify_indicators(indicator_weights, "dampened", relevant_indicators)
    boosted = _classify_indicators(indicator_weights, "boosted", relevant_indicators)
    watchlist = _classify_indicators(indicator_weights, "watchlist", relevant_indicators)

    lines = ["## Customer Weight History", ""]
    lines.append("Use this as calibrated guidance from recent officer outcomes.")

    blend_line = _format_blend_line(blend_weights)
    if blend_line:
        lines.append(f"\n### {blend_line}")

    if dampened:
        lines.append("\n### Dampened Signals (treat as weaker evidence)")
        lines.extend(dampened)

    if boosted:
        lines.append("\n### Boosted Signals (treat as stronger evidence)")
        lines.extend(boosted)

    if watchlist:
        lines.append("\n### Emerging Signals (trend only, not decisive alone)")
        lines.extend(watchlist)

    if not dampened and not boosted and not watchlist:
        lines.append("\n### Signal Status")
        lines.append("- No strong per-indicator shifts yet; use full constellation evidence.")

    return "\n".join(lines)


def _classify_indicators(
    weights: dict[str, Any],
    category: str,
    relevant: list[str] | None,
) -> list[str]:
    """Return formatted lines for dampened or boosted indicators."""
    lines: list[tuple[float, str]] = []
    for name, meta in weights.items():
        if relevant and name not in relevant:
            continue

        if isinstance(meta, dict):
            multiplier = _safe_float(meta.get("multiplier"), 1.0)
            sample = int(
                _safe_float(
                    meta.get("sample_size")
                    or meta.get("total_fires")
                    or meta.get("total")
                    or 0,
                    0.0,
                )
            )
            precision = _safe_float(meta.get("precision"), 0.5)
            raw_precision = _safe_float(meta.get("raw_precision"), precision)
            reason = str(meta.get("reason") or "").strip()
        else:
            multiplier = _safe_float(meta, 1.0)
            sample = 0
            precision = 0.5
            raw_precision = 0.5
            reason = ""

        if sample < MIN_SAMPLE_DISPLAY:
            continue

        if category == "dampened" and multiplier >= DAMPENED_THRESHOLD:
            continue
        if category == "boosted" and multiplier <= BOOSTED_THRESHOLD:
            continue
        if category == "watchlist":
            if multiplier < DAMPENED_THRESHOLD or multiplier > BOOSTED_THRESHOLD:
                continue
            if abs(multiplier - 1.0) < WATCHLIST_DELTA:
                continue

        delta_pct = (multiplier - 1.0) * 100.0
        direction = "downweighted" if delta_pct < 0 else "upweighted"
        confidence = _sample_confidence(sample)
        line = (
            f"- **{name}** - {multiplier:.2f}x ({direction} {abs(delta_pct):.0f}%, "
            f"sample {sample}, precision {precision:.2f}, raw {raw_precision:.2f}, "
            f"evidence {confidence})"
        )
        if reason:
            line += f"; note: {reason}"

        lines.append((abs(multiplier - 1.0), line))

    lines.sort(key=lambda item: item[0], reverse=True)
    return [line for _, line in lines]


def _format_blend_line(blend_weights: dict[str, float] | None) -> str:
    if not blend_weights:
        return "Blend: rule engine 50% / investigators 50% (balanced)"

    rule_w = _safe_float(blend_weights.get("rule_engine"), DEFAULT_RULE_WEIGHT)
    inv_w = _safe_float(blend_weights.get("investigators"), DEFAULT_INVESTIGATOR_WEIGHT)

    if rule_w >= 0.55:
        stance = "leans rule-engine evidence"
    elif rule_w <= 0.45:
        stance = "leans investigator evidence"
    else:
        stance = "balanced"

    return f"Blend: rule engine {rule_w:.0%} / investigators {inv_w:.0%} ({stance})"


def _sample_confidence(sample: int) -> str:
    if sample >= 8:
        return "high"
    if sample >= 4:
        return "medium"
    return "early"


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
