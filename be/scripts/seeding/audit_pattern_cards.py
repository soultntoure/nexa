"""Pattern card data for audit candidates — extracted for file size."""

PATTERN_CARD_ATO = {
    "pattern_type": "identity_access",
    "summary": (
        "Multiple accounts show impossible travel patterns combined with "
        "new device appearances at the destination. Kyiv to São Paulo in "
        "under 35 minutes with a previously unseen macOS device."
    ),
    "indicators": [
        "impossible_travel",
        "new_device_at_destination",
        "ip_country_mismatch",
    ],
    "agent_report": {
        "investigator": "identity_access",
        "score": 0.78,
        "confidence": 0.83,
        "reasoning": (
            "Geographic impossibility detected: last known IP in Kyiv (UKR) "
            "35 minutes before request from São Paulo (BRA). New macOS 14 "
            "device appeared at destination — never seen on this account. "
            "Combined with 4x normal withdrawal amount, this strongly suggests "
            "account takeover via stolen credentials."
        ),
        "evidence_sources": [
            "ip_history (2 entries, 35min gap)",
            "devices (new device first_seen 5min ago)",
            "withdrawals (amount 4x historical avg)",
        ],
    },
    "affected_customers": ["CUST-016"],
    "recommended_action": "Block withdrawal, trigger ATO verification flow",
}

PATTERN_CARD_DEPOSIT_RUN = {
    "pattern_type": "financial_behavior",
    "summary": (
        "Cluster of new accounts (< 2 weeks) depositing via card then "
        "requesting near-full withdrawal with minimal or zero trading. "
        "Shared device fingerprints link Victor-Sophie and Ahmed-Fatima pairs."
    ),
    "indicators": [
        "no_trade_withdrawal",
        "shared_device_fingerprint",
        "near_full_balance_withdrawal",
        "new_account",
    ],
    "agent_report": {
        "investigator": "financial_behavior",
        "score": 0.82,
        "confidence": 0.79,
        "reasoning": (
            "Classic deposit-and-run pattern across 4 linked accounts. "
            "Victor deposited $3k, placed 1 token trade ($10, 15s), withdrawing "
            "$2990. Sophie had 3 failed cards before success, 2 trades ($5 each), "
            "withdrawing 96%. Both share device fingerprint a1b2c3d4. Ahmed and "
            "Fatima share different fingerprint deadbeef + same IP + same "
            "third-party recipient 'Mohamed Nour'."
        ),
        "evidence_sources": [
            "trades (0-1 trades per account, <1min duration)",
            "devices (shared fingerprints across account pairs)",
            "transactions (failed card_restricted errors)",
            "withdrawals (>95% of deposit amount)",
        ],
    },
    "affected_customers": ["CUST-011", "CUST-012", "CUST-013", "CUST-014"],
    "recommended_action": (
        "Block all 4 accounts, escalate to fraud ring investigation"
    ),
}

PATTERN_CARD_MULE = {
    "pattern_type": "cross_account",
    "summary": (
        "Existing Ahmed/Fatima fraud ring (CUST-013/014) has expanded with "
        "a new mule account (CUST-020 Priya). Shared device fingerprint, "
        "same third-party recipient, IP in same subnet. Zero trades, "
        "pure deposit-to-withdrawal pass-through."
    ),
    "indicators": [
        "shared_device_fingerprint",
        "shared_recipient",
        "ip_subnet_cluster",
        "zero_trade_passthrough",
        "new_account",
    ],
    "agent_report": {
        "investigator": "cross_account",
        "score": 0.92,
        "confidence": 0.87,
        "reasoning": (
            "CUST-020 shares device fingerprint deadbeef with CUST-013/014. "
            "Same third-party recipient 'Mohamed Nour'. IP 41.44.55.77 is in "
            "same /24 subnet as ring IP 41.44.55.66. 3-day account with zero "
            "trades and $4800 withdrawal (96% of deposits). This is a mule "
            "account layering funds for the Ahmed/Fatima ring."
        ),
        "evidence_sources": [
            "devices (shared fingerprint deadbeef across 3 accounts)",
            "withdrawals (same recipient 'Mohamed Nour' across 3 accounts)",
            "ip_history (41.44.55.* subnet cluster)",
            "trades (0 trades on mule, token trades on ring accounts)",
        ],
    },
    "affected_customers": ["CUST-013", "CUST-014", "CUST-020"],
    "recommended_action": (
        "Block CUST-020, link to existing ring investigation, "
        "monitor 41.44.55.0/24 subnet for new account signups"
    ),
}
