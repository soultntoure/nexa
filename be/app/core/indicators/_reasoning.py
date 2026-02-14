"""Human-readable reasoning builders for each fraud indicator."""


def build_amount_reasoning(evidence: dict, score: float, amount: float) -> str:
    """Explain withdrawal amount risk in plain English."""
    count = evidence.get("count", 0)
    avg = evidence.get("avg", 0)
    z = evidence.get("z_score")

    if count < 2:
        return (
            f"There is limited withdrawal history for this customer "
            f"({count} prior withdrawal{'s' if count != 1 else ''}), "
            f"so the amount cannot be compared to a baseline."
        )

    if score == 0.0:
        return (
            f"This withdrawal of ${amount:,.0f} is consistent with the "
            f"customer's typical withdrawal range (average ${avg:,.0f})."
        )
    if score <= 0.3:
        return (
            f"This withdrawal of ${amount:,.0f} is slightly above the "
            f"customer's average of ${avg:,.0f}, but within a reasonable range."
        )
    if score <= 0.50:
        return (
            f"This withdrawal of ${amount:,.0f} is unusually large compared "
            f"to the customer's average of ${avg:,.0f}. This warrants attention."
        )
    return (
        f"This withdrawal of ${amount:,.0f} is an extreme outlier — far above "
        f"the customer's average of ${avg:,.0f}. This is highly unusual."
    )


def build_velocity_reasoning(evidence: dict, score: float) -> str:
    """Explain withdrawal frequency risk in plain English."""
    c1h = evidence.get("count_1h", 0)
    c24h = evidence.get("count_24h", 0)
    c7d = evidence.get("count_7d", 0)
    baseline_24h = float(evidence.get("baseline_24h", 0.0))
    r1h = float(evidence.get("spike_ratio_1h", 0.0))
    r24h = float(evidence.get("spike_ratio_24h", 0.0))
    r7d = float(evidence.get("spike_ratio_7d", 0.0))
    strongest_spike = max(r1h, r24h, r7d)

    if score == 0.0:
        return (
            f"Withdrawal frequency is normal — "
            f"{c24h} request{'s' if c24h != 1 else ''} in the past 24 hours, "
            f"close to this customer's normal pace."
        )
    if score < 0.55:
        return (
            f"Withdrawal frequency is elevated — "
            f"{c1h} in the past hour, {c24h} in 24 hours, "
            f"and {c7d} in the past week. This is about "
            f"{strongest_spike:.1f}x above the customer's baseline cadence."
        )
    return (
        f"Withdrawal frequency is very high — "
        f"{c1h} requests in the past hour, {c24h} in 24 hours, "
        f"and {c7d} in the past week versus a baseline of "
        f"{baseline_24h:.1f}/day. This resembles rapid fund extraction "
        f"and should be reviewed with other signals."
    )


def build_payment_method_reasoning(
    evidence: dict, score: float, reasons: list[str],
) -> str:
    """Explain payment method risk in plain English."""
    age_days = evidence.get("age_days", 0)

    if score == 0.0:
        if age_days >= 365:
            return (
                "The payment method has been verified and "
                f"in use for over {int(age_days // 365)} year"
                f"{'s' if age_days >= 730 else ''}."
            )
        return (
            "The payment method is verified and has been "
            f"on file for {int(age_days)} days."
        )

    parts = []
    if evidence.get("is_blacklisted"):
        parts.append("The payment method has been flagged on a blacklist.")
    if not evidence.get("is_verified"):
        parts.append("The payment method has not been verified.")
    if age_days < 7:
        parts.append(
            f"It was added only {int(age_days)} day"
            f"{'s' if age_days != 1 else ''} ago."
        )
    elif age_days < 30:
        parts.append(f"It was added recently ({int(age_days)} days ago).")
    churn = evidence.get("methods_added_30d", 0)
    if churn >= 3:
        parts.append(
            f"The customer has added {churn} payment methods "
            f"in the last 30 days, suggesting method switching."
        )
    return " ".join(parts) if parts else "The payment method has known risk factors."


def build_geographic_reasoning(evidence: dict, score: float) -> str:
    """Explain geographic risk in plain English."""
    is_vpn = evidence.get("is_vpn", False)
    country_match = evidence.get("country_match", True)
    current = evidence.get("current_location", "")
    home = evidence.get("home_country", "")
    distinct = evidence.get("distinct_countries_7d", 0)

    if score == 0.0:
        return "The customer is connecting from their registered country with no VPN detected."

    parts = []
    if is_vpn:
        loc_desc = f" from {current}" if current else ""
        parts.append(f"A VPN connection was detected{loc_desc} (common on this platform, noted but not penalized heavily).")
    if not country_match:
        parts.append(
            f"The connection country does not match the customer's "
            f"registered country ({home})."
        )
    if distinct >= 2:
        parts.append(
            f"Activity from {distinct} different countries in the past week."
        )
    return " ".join(parts) if parts else "Geographic signals indicate some risk."


def build_device_reasoning(evidence: dict, score: float) -> str:
    """Explain device fingerprint risk in plain English."""
    known = evidence.get("known", evidence.get("is_trusted"))

    if known is False and evidence.get("fingerprint") is not None:
        return (
            "This device has never been used by the customer before. "
            "New devices on withdrawal requests increase risk."
        )

    parts = []
    shared = evidence.get("shared_account_count", 1)
    if shared >= 3:
        parts.append(
            f"This device is shared across {shared} different accounts, "
            f"which is a strong indicator of organized fraud."
        )
    elif shared == 2:
        parts.append("This device is shared with one other account.")

    if not evidence.get("is_trusted", True):
        parts.append("The device has not been marked as trusted.")

    age = evidence.get("device_age_days", 0)
    if age < 1:
        parts.append("The device was registered less than a day ago.")
    elif age < 7:
        parts.append(f"The device is relatively new ({int(age)} days old).")

    if not parts:
        return "The device is known and trusted for this customer."
    return " ".join(parts)


def build_trading_reasoning(
    evidence: dict, score: float, amount: float,
) -> str:
    """Explain trading behavior risk in plain English."""
    trades = evidence.get("trade_count", 0)
    deposits = evidence.get("total_deposits", 0)
    ratio = evidence.get("withdraw_deposit_ratio", 0)

    if score == 0.0:
        return "The customer has a healthy trading history with normal withdrawal patterns."

    parts = []
    if trades == 0:
        parts.append("The customer has made zero trades since opening their account")
    elif trades < 3:
        parts.append(f"The customer has made only {trades} trade{'s' if trades != 1 else ''}")
    elif trades < 5:
        parts.append(f"The customer has relatively few trades ({trades})")

    if ratio >= 0.9:
        parts.append(
            f"and is withdrawing {ratio:.0%} of deposited funds "
            f"(${amount:,.0f} of ${deposits:,.0f})"
        )
    elif ratio >= 0.7:
        parts.append(
            f"and is withdrawing a large portion ({ratio:.0%}) of deposited funds"
        )

    joined = " ".join(parts)
    if trades <= 2 and ratio >= 0.9:
        return f"{joined}. This resembles a deposit-and-withdraw pattern."
    if parts:
        return f"{joined}."
    return "Trading activity shows some risk indicators."


def build_recipient_reasoning(
    evidence: dict, score: float, recipient_name: str,
) -> str:
    """Explain recipient risk in plain English."""
    if not evidence:
        return "Customer information could not be retrieved for recipient analysis."

    name_match = evidence.get("name_match", True)
    cross = evidence.get("cross_account_count", 0)
    history = evidence.get("history_with_recipient", 0)

    if score == 0.0:
        return "The recipient name matches the account holder and has prior transaction history."

    parts = []
    if not name_match:
        parts.append(
            f"The recipient name '{recipient_name}' does not match "
            f"the account holder"
        )
    if cross >= 3:
        parts.append(
            f"this recipient has received funds from {cross} different accounts"
        )
    elif cross == 2:
        parts.append("this recipient has received funds from 2 accounts")
    if history == 0:
        parts.append("this is the first withdrawal to this recipient")

    if not parts:
        return "Some recipient risk factors were detected."

    joined = ", and ".join(parts) if len(parts) == 2 else ", ".join(parts)
    return joined[0].upper() + joined[1:] + "."


def build_card_errors_reasoning(evidence: dict, score: float) -> str:
    """Explain card error history risk in plain English."""
    fails = evidence.get("fail_count_30d", 0)
    methods = evidence.get("distinct_methods_30d", 0)

    if score == 0.0:
        return "No failed transactions or unusual payment method changes in the past 30 days."

    parts = []
    if fails >= 5:
        parts.append(f"There have been {fails} failed transactions in the past 30 days.")
    elif fails >= 2:
        parts.append(f"There have been {fails} failed transactions in the past 30 days.")
    if methods >= 4:
        parts.append(
            f"The customer has used {methods} different payment methods in 30 days, "
            f"suggesting rapid method switching."
        )
    elif methods >= 3:
        parts.append(
            f"The customer has used {methods} different payment methods in 30 days."
        )
    return " ".join(parts) if parts else "Some transaction error patterns were detected."
