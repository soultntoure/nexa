"""Pure scoring functions for each fraud indicator — no DB, fully testable."""

from app.core.indicators._reasoning import (
    build_amount_reasoning,
    build_card_errors_reasoning,
    build_device_reasoning,
    build_geographic_reasoning,
    build_payment_method_reasoning,
    build_recipient_reasoning,
    build_trading_reasoning,
    build_velocity_reasoning,
)


def score_velocity(evidence: dict) -> tuple[float, str]:
    c1h = evidence["count_1h"]
    c24h = evidence["count_24h"]
    c7d = evidence["count_7d"]
    c30d = evidence["count_30d"]

    baselines = _velocity_baselines(c24h, c30d)
    ratios = _velocity_spike_ratios(c1h, c24h, c7d, baselines)

    warn_threshold = c1h >= 4 or c24h >= 7 or c7d >= 12
    critical_threshold = c1h >= 6 or c24h >= 10 or c7d >= 18
    warn_spike = any(v >= 2.5 for v in ratios.values())
    critical_spike = any(v >= 4.0 for v in ratios.values())

    score = 0.0
    if warn_threshold:
        score = 0.25
    if warn_threshold and warn_spike:
        score = max(score, 0.40)
    if critical_threshold:
        score = max(score, 0.50)
    if critical_threshold and critical_spike:
        score = max(score, 0.65)

    full_evidence = {
        **evidence,
        **baselines,
        **ratios,
        "warn_threshold_hit": warn_threshold,
        "critical_threshold_hit": critical_threshold,
        "warn_spike_hit": warn_spike,
        "critical_spike_hit": critical_spike,
    }
    return min(score, 0.65), build_velocity_reasoning(full_evidence, min(score, 0.65))


def _velocity_baselines(c24h: int, c30d: int) -> dict:
    historical_29d = max(c30d - c24h, 0)
    baseline_24h = historical_29d / 29.0 if historical_29d > 0 else c30d / 30.0
    return {
        "baseline_1h": baseline_24h / 24.0,
        "baseline_24h": baseline_24h,
        "baseline_7d": baseline_24h * 7.0,
    }


def _velocity_spike_ratios(c1h: int, c24h: int, c7d: int, baselines: dict) -> dict:
    return {
        "spike_ratio_1h": c1h / max(baselines["baseline_1h"], 0.5),
        "spike_ratio_24h": c24h / max(baselines["baseline_24h"], 1.5),
        "spike_ratio_7d": c7d / max(baselines["baseline_7d"], 3.0),
    }


def score_amount_anomaly(evidence: dict) -> tuple[float, str]:
    amount = evidence["amount"]
    avg = evidence["avg"]
    std = evidence["std"]
    count = evidence["count"]

    if count < 2 or std == 0:
        score = 0.3 if count == 0 else 0.15
        sparse = {**evidence, "z_score": None}
        return score, build_amount_reasoning(sparse, score, amount)

    z = (amount - avg) / std
    full_evidence = {**evidence, "z_score": round(z, 2)}

    if z <= 1.0:
        score = 0.0
    elif z <= 2.0:
        score = 0.25
    elif z <= 3.0:
        score = 0.40
    else:
        score = min(0.75, 0.40 + (z - 3.0) * 0.08)

    return score, build_amount_reasoning(full_evidence, score, amount)


def score_payment_method(evidence: dict) -> tuple[float, str]:
    if not evidence:
        return 0.3, "No payment method is on file for this customer, which prevents verification."

    age_days = evidence["age_days"]
    is_blacklisted = evidence["is_blacklisted"]
    is_verified = evidence["is_verified"]
    churn_30d = evidence["methods_added_30d"]

    score = 0.0
    reasons = []

    if is_blacklisted:
        score += 0.5
        reasons.append("Blacklisted method")
    if not is_verified:
        score += 0.2
        reasons.append("Unverified")
    if age_days < 7:
        score += 0.3
        reasons.append(f"New method ({age_days:.0f}d old)")
    elif age_days < 30:
        score += 0.1
        reasons.append(f"Recent method ({age_days:.0f}d old)")
    if churn_30d >= 3:
        score += 0.2
        reasons.append(f"{churn_30d} methods added in 30d")

    score = round(min(score, 1.0), 2)
    return score, build_payment_method_reasoning(evidence, score, reasons)


def score_geographic(evidence: dict) -> tuple[float, str]:
    rows = evidence.pop("rows", [])
    distinct_7d = evidence["distinct_7d"]
    historical_countries = evidence["historical_countries"]
    customer_country = evidence.pop("customer_country", "")

    if not rows:
        return 0.2, "No IP connection history is available for this customer."

    latest = rows[0]
    is_vpn = bool(latest["is_vpn"])
    home = (customer_country or "").upper()
    current_loc = str(latest["location"] or "")
    current_country = current_loc.split(", ")[-1].strip().upper() if current_loc else ""
    country_match = home == current_country if home and current_country else True
    dampen = _traveler_dampen_factor(historical_countries)

    full_evidence = {
        "is_vpn": is_vpn,
        "country_match": country_match,
        "distinct_countries_7d": distinct_7d,
        "historical_countries": historical_countries,
        "dampen_factor": round(dampen, 2),
        "current_location": current_loc,
        "home_country": home,
    }

    score = 0.0
    if is_vpn:
        score += 0.05
    if not country_match:
        score += 0.15 * dampen
    if distinct_7d >= 4:
        score += 0.20 * dampen
    elif distinct_7d >= 2:
        score += 0.05 * dampen

    score = round(min(score, 1.0), 2)
    return score, build_geographic_reasoning(full_evidence, score)


def _traveler_dampen_factor(historical_countries: int) -> float:
    if historical_countries <= 1:
        return 1.0
    if historical_countries == 2:
        return 0.7
    if historical_countries == 3:
        return 0.5
    if historical_countries == 4:
        return 0.4
    return 0.3


def score_device_fingerprint(evidence: dict) -> tuple[float, str]:
    if not evidence.get("is_trusted") and evidence.get("known") is False:
        return 0.4, build_device_reasoning(evidence, 0.4)

    is_trusted = evidence.get("is_trusted", True)
    age_days = evidence.get("device_age_days", 0)
    shared = evidence.get("shared_account_count", 1)

    score = 0.0
    if shared >= 3:
        score += 0.7
    elif shared == 2:
        score += 0.4
    if not is_trusted:
        score += 0.25
    if age_days < 1:
        score += 0.25
    elif age_days < 7:
        score += 0.15

    score = round(min(score, 1.0), 2)
    return score, build_device_reasoning(evidence, score)


def score_trading_behavior(evidence: dict) -> tuple[float, str]:
    amount = evidence["amount"]
    deposits = evidence["total_deposits"]
    trades = evidence["trade_count"]

    ratio = amount / deposits if deposits > 0 else 999.0
    full_evidence = {**evidence, "withdraw_deposit_ratio": round(ratio, 2)}

    score = 0.0
    if trades == 0:
        score += 0.6
    elif trades < 3:
        score += 0.35
    elif trades < 5:
        score += 0.15

    if ratio >= 0.9:
        score += 0.4
    elif ratio >= 0.7:
        score += 0.25

    score = round(min(score, 1.0), 2)
    return score, build_trading_reasoning(full_evidence, score, amount)


def score_recipient(evidence: dict) -> tuple[float, str]:
    if not evidence:
        return 0.3, "Customer information could not be retrieved for recipient analysis."

    recipient_name = evidence.get("recipient_name", "")
    customer_name = evidence.get("customer_name", "")
    cross_accounts = evidence.get("cross_account_count", 0)
    history = evidence.get("history_count", 0)
    name_match = customer_name.lower().strip() == recipient_name.lower().strip()

    full_evidence = {
        "name_match": name_match,
        "cross_account_count": cross_accounts,
        "history_with_recipient": history,
    }

    score = 0.0
    if not name_match:
        score += 0.3
    if cross_accounts >= 3:
        score += 0.4
    elif cross_accounts == 2:
        score += 0.2
    if history == 0:
        score += 0.2

    score = round(min(score, 1.0), 2)
    return score, build_recipient_reasoning(full_evidence, score, recipient_name)


def score_card_errors(evidence: dict) -> tuple[float, str]:
    fails = evidence["fail_count_30d"]
    methods = evidence["distinct_methods_30d"]

    score = 0.0
    if fails >= 5:
        score += 0.5
    elif fails >= 2:
        score += 0.2
    if methods >= 4:
        score += 0.4
    elif methods >= 3:
        score += 0.2

    score = round(min(score, 1.0), 2)
    return score, build_card_errors_reasoning(evidence, score)
