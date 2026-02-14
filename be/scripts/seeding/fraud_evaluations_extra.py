"""Seed evaluations + indicator results + decisions for CUST-017 to CUST-022."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import Evaluation, IndicatorResult, WithdrawalDecision

from .constants import NOW, _ago, _id

# ── Per-customer evaluation configs ──
_EVAL_CONFIGS: list[dict] = [
    {
        "customer": "liam",
        "wd_key": "liam.wd.pending",
        "composite_score": 0.72,
        "decision": "blocked",
        "risk_level": "high",
        "summary": "Refund abuse: 3 chargebacks in 30 days across different cards.",
        "investigation_data": {
            "triage": {
                "constellation_analysis": (
                    "Chargeback cluster across 3 cards in 30 days signals refund "
                    "abuse. Profitable trading history makes legitimate dispute "
                    "unlikely — customer exploiting chargeback process."
                ),
                "assignments": [
                    {"investigator": "financial_behavior", "priority": "high"},
                ],
                "elapsed_s": 2.8,
            },
            "investigators": [{
                "name": "financial_behavior",
                "score": 0.75,
                "confidence": 0.82,
                "reasoning": (
                    "3 chargebacks across 3 different cards within 30 days. "
                    "All disputes filed after profitable BTC trades. Classic "
                    "refund abuse — profit from trades then reverse deposits."
                ),
                "elapsed_s": 7.2,
            }],
        },
        "indicators": [
            ("velocity", 0.40, 1.0, 0.85, "3 deposits flagged as chargebacks."),
            ("amount_anomaly", 0.55, 1.0, 0.80, "$3500 withdrawal after chargebacks."),
            ("no_trade", 0.10, 1.0, 0.95, "Has trading history — not a no-trade case."),
            ("card_errors", 0.90, 1.5, 0.92, "3 chargeback errors in 30 days."),
            ("geographic", 0.10, 1.0, 0.90, "Consistent Singapore IP."),
            ("rapid_funding", 0.30, 1.0, 0.80, "No rapid funding cycles detected."),
            ("device_fingerprint", 0.15, 1.5, 0.90, "Single device, consistent."),
            ("recipient", 0.20, 1.0, 0.85, "Self-named recipient, expected."),
        ],
    },
    {
        "customer": "olga",
        "wd_key": "olga.wd.pending",
        "composite_score": 0.85,
        "decision": "blocked",
        "risk_level": "high",
        "summary": "Structuring: 12x $990 deposits under threshold, $11k withdrawal.",
        "investigation_data": {
            "triage": {
                "constellation_analysis": (
                    "12 deposits of exactly $990 — just under $1000 reporting "
                    "threshold. 2-day account with zero trades. Classic smurfing "
                    "pattern to aggregate funds below detection limits."
                ),
                "assignments": [
                    {"investigator": "financial_behavior", "priority": "high"},
                ],
                "elapsed_s": 2.5,
            },
            "investigators": [{
                "name": "financial_behavior",
                "score": 0.88,
                "confidence": 0.91,
                "reasoning": (
                    "12 deposits of $990 each over 36 hours — consistent amount "
                    "just below $1000 reporting threshold. Zero trades on 2-day "
                    "account. Single $11k withdrawal. Textbook structuring."
                ),
                "elapsed_s": 6.8,
            }],
        },
        "indicators": [
            ("velocity", 0.85, 1.0, 0.90, "12 deposits in 36 hours."),
            ("amount_anomaly", 0.90, 1.0, 0.92, "$990 repeating — threshold evasion."),
            ("no_trade", 0.95, 1.0, 0.95, "Zero trades on funded account."),
            ("card_errors", 0.05, 1.5, 0.90, "No card errors."),
            ("geographic", 0.10, 1.0, 0.85, "Consistent Moscow IP."),
            ("rapid_funding", 0.80, 1.0, 0.88, "12 deposits → 1 withdrawal cycle."),
            ("device_fingerprint", 0.15, 1.5, 0.90, "Single device."),
            ("recipient", 0.20, 1.0, 0.85, "Self-named recipient."),
        ],
    },
    {
        "customer": "dmitri",
        "wd_key": "dmitri.wd.pending",
        "composite_score": 0.82,
        "decision": "blocked",
        "risk_level": "high",
        "summary": "ATO: dormant 6mo, new device + new country, $8k withdrawal.",
        "investigation_data": {
            "triage": {
                "constellation_analysis": (
                    "6-month dormant account suddenly active from new country "
                    "(NGA vs historical RUS). Brand new device never seen before. "
                    "$8k withdrawal — entire balance. Classic credential stuffing ATO."
                ),
                "assignments": [
                    {"investigator": "identity_access", "priority": "high"},
                    {"investigator": "financial_behavior", "priority": "medium"},
                ],
                "elapsed_s": 3.1,
            },
            "investigators": [
                {
                    "name": "identity_access",
                    "score": 0.90,
                    "confidence": 0.88,
                    "reasoning": (
                        "Account dormant 180 days. New macOS device appeared 30min "
                        "ago from Lagos, NGA — historical activity from Saint "
                        "Petersburg, RUS. Device shared with CUST-022. Impossible "
                        "geographic transition. Strong ATO indicators."
                    ),
                    "elapsed_s": 8.1,
                },
                {
                    "name": "financial_behavior",
                    "score": 0.78,
                    "confidence": 0.85,
                    "reasoning": (
                        "$8k withdrawal is entire account balance. No new deposits "
                        "or trades — just draining. Consistent with account takeover "
                        "where attacker extracts maximum value immediately."
                    ),
                    "elapsed_s": 7.5,
                },
            ],
        },
        "indicators": [
            ("velocity", 0.20, 1.0, 0.85, "Single withdrawal, low velocity."),
            ("amount_anomaly", 0.75, 1.0, 0.88, "$8k — entire balance drain."),
            ("no_trade", 0.60, 1.0, 0.80, "No recent trades (6mo dormant)."),
            ("card_errors", 0.05, 1.5, 0.90, "No card errors."),
            ("geographic", 0.95, 1.0, 0.92, "RUS→NGA impossible travel."),
            ("rapid_funding", 0.15, 1.0, 0.85, "No rapid funding cycle."),
            ("device_fingerprint", 0.85, 1.5, 0.90, "New device, shared with CUST-022."),
            ("recipient", 0.20, 1.0, 0.85, "Self-named recipient."),
        ],
    },
    {
        "customer": "priya",
        "wd_key": "priya.wd.pending",
        "composite_score": 0.88,
        "decision": "blocked",
        "risk_level": "high",
        "summary": "Mule account: linked to Ahmed/Fatima ring, zero trades.",
        "investigation_data": {
            "triage": {
                "constellation_analysis": (
                    "3-day account with zero trades. Shares device fingerprint "
                    "with known fraud ring (CUST-013/014). Same recipient "
                    "'Mohamed Nour'. Pure deposit-to-withdrawal pass-through."
                ),
                "assignments": [
                    {"investigator": "cross_account", "priority": "high"},
                    {"investigator": "financial_behavior", "priority": "medium"},
                ],
                "elapsed_s": 2.9,
            },
            "investigators": [
                {
                    "name": "cross_account",
                    "score": 0.92,
                    "confidence": 0.90,
                    "reasoning": (
                        "Device fingerprint matches CUST-013 (Ahmed) and CUST-014 "
                        "(Fatima) — confirmed fraud ring. Same third-party recipient "
                        "'Mohamed Nour'. IP in fraud ring range. Mule account "
                        "facilitating fund pass-through for ring."
                    ),
                    "elapsed_s": 9.0,
                },
                {
                    "name": "financial_behavior",
                    "score": 0.85,
                    "confidence": 0.87,
                    "reasoning": (
                        "Zero trades on 3-day account. $5000 deposited, $4800 "
                        "withdrawal (96%). Classic mule pattern — no economic "
                        "activity, pure fund transfer vehicle."
                    ),
                    "elapsed_s": 7.0,
                },
            ],
        },
        "indicators": [
            ("velocity", 0.30, 1.0, 0.80, "2 deposits, 1 withdrawal — moderate."),
            ("amount_anomaly", 0.70, 1.0, 0.85, "96% withdrawal ratio."),
            ("no_trade", 0.95, 1.0, 0.95, "Zero trades — pure pass-through."),
            ("card_errors", 0.05, 1.5, 0.90, "No card errors."),
            ("geographic", 0.25, 1.0, 0.80, "Single IP, consistent."),
            ("rapid_funding", 0.65, 1.0, 0.85, "Deposit→withdraw in 2 days."),
            ("device_fingerprint", 0.95, 1.5, 0.95, "Shared with fraud ring."),
            ("recipient", 0.90, 1.0, 0.92, "Third-party 'Mohamed Nour' — ring link."),
        ],
    },
    {
        "customer": "hassan_r",
        "wd_key": "hassan_r.wd.pending",
        "composite_score": 0.68,
        "decision": "escalated",
        "risk_level": "medium",
        "summary": "Bonus abuse: micro-trades to meet requirement, instant cashout.",
        "investigation_data": {
            "triage": {
                "constellation_analysis": (
                    "1-day account with 3 micro-trades ($1 each, 10s duration) — "
                    "minimum to qualify for welcome bonus. Immediate $600 withdrawal "
                    "(deposit $500 + $100 bonus). Bonus exploitation pattern."
                ),
                "assignments": [
                    {"investigator": "financial_behavior", "priority": "high"},
                ],
                "elapsed_s": 2.6,
            },
            "investigators": [{
                "name": "financial_behavior",
                "score": 0.72,
                "confidence": 0.80,
                "reasoning": (
                    "3 trades of $1 each lasting 10 seconds — clearly meeting "
                    "minimum trading requirement. $600 withdrawal = deposit + "
                    "bonus. Account 1 day old. Bonus abuse pattern."
                ),
                "elapsed_s": 6.5,
            }],
        },
        "indicators": [
            ("velocity", 0.20, 1.0, 0.80, "Low velocity — 1 deposit, 1 withdrawal."),
            ("amount_anomaly", 0.50, 1.0, 0.78, "$600 withdrawal > $500 deposit."),
            ("no_trade", 0.70, 1.0, 0.85, "3 micro-trades — effectively no trading."),
            ("card_errors", 0.05, 1.5, 0.90, "No card errors."),
            ("geographic", 0.10, 1.0, 0.85, "Consistent Dubai IP."),
            ("rapid_funding", 0.75, 1.0, 0.85, "Deposit→withdraw in 20 hours."),
            ("device_fingerprint", 0.15, 1.5, 0.90, "Single device."),
            ("recipient", 0.20, 1.0, 0.85, "Self-named recipient."),
        ],
    },
    {
        "customer": "elena",
        "wd_key": "elena.wd.pending",
        "composite_score": 0.80,
        "decision": "blocked",
        "risk_level": "high",
        "summary": "Synthetic identity: mismatched country/IP, shared ATO device.",
        "investigation_data": {
            "triage": {
                "constellation_analysis": (
                    "Registered as Romanian but IP from Lagos, NGA. Shares device "
                    "with Dmitri Kozlov (CUST-019) — ATO cluster. 1-day account, "
                    "1 token trade, withdrawing 97%. Synthetic identity indicators."
                ),
                "assignments": [
                    {"investigator": "identity_access", "priority": "high"},
                    {"investigator": "cross_account", "priority": "high"},
                ],
                "elapsed_s": 3.0,
            },
            "investigators": [
                {
                    "name": "identity_access",
                    "score": 0.85,
                    "confidence": 0.87,
                    "reasoning": (
                        "Country registration (ROU) mismatches IP geolocation "
                        "(Lagos, NGA). Brand new account from suspicious location. "
                        "Profile inconsistencies suggest assembled identity."
                    ),
                    "elapsed_s": 7.8,
                },
                {
                    "name": "cross_account",
                    "score": 0.82,
                    "confidence": 0.85,
                    "reasoning": (
                        "Device fingerprint shared with CUST-019 (Dmitri Kozlov) "
                        "who is flagged for ATO. Same IP subnet. Suggests same "
                        "actor operating multiple fraudulent accounts."
                    ),
                    "elapsed_s": 8.2,
                },
            ],
        },
        "indicators": [
            ("velocity", 0.15, 1.0, 0.80, "Single deposit + withdrawal."),
            ("amount_anomaly", 0.65, 1.0, 0.82, "97% withdrawal ratio."),
            ("no_trade", 0.80, 1.0, 0.90, "1 token trade ($5, 20s)."),
            ("card_errors", 0.05, 1.5, 0.90, "No card errors."),
            ("geographic", 0.90, 1.0, 0.90, "ROU registration, NGA IP."),
            ("rapid_funding", 0.60, 1.0, 0.82, "Deposit→withdraw in 10 hours."),
            ("device_fingerprint", 0.90, 1.5, 0.92, "Shared with CUST-019 (ATO)."),
            ("recipient", 0.20, 1.0, 0.85, "Self-named recipient."),
        ],
    },
]


async def _seed_evaluations_extra(s: AsyncSession) -> None:
    """Create evaluations, indicator results, and decisions for CUST-017–022."""
    for cfg in _EVAL_CONFIGS:
        wd_id = _id(cfg["wd_key"])
        eval_id = _id(f"{cfg['customer']}.eval")

        s.add(Evaluation(
            id=eval_id,
            withdrawal_id=wd_id,
            composite_score=cfg["composite_score"],
            decision=cfg["decision"],
            risk_level=cfg["risk_level"],
            summary=cfg["summary"],
            investigation_data=cfg["investigation_data"],
            has_hard_escalation=cfg["decision"] == "blocked",
            has_multi_critical=cfg["composite_score"] >= 0.70,
            gray_zone_used=False,
            elapsed_s=_total_elapsed(cfg["investigation_data"]),
            checked_at=NOW,
        ))

        for name, score, weight, confidence, reasoning in cfg["indicators"]:
            s.add(IndicatorResult(
                id=uuid.uuid4(),
                withdrawal_id=wd_id,
                evaluation_id=eval_id,
                indicator_name=name,
                score=score,
                weight=weight,
                confidence=confidence,
                reasoning=reasoning,
                evidence={"source": "seed", "score": score},
                created_at=NOW,
            ))

        s.add(WithdrawalDecision(
            id=uuid.uuid4(),
            withdrawal_id=wd_id,
            evaluation_id=eval_id,
            decision=cfg["decision"],
            composite_score=cfg["composite_score"],
            reasoning=cfg["summary"],
            decided_at=NOW,
            created_at=NOW,
        ))


def _total_elapsed(investigation_data: dict) -> float:
    """Sum triage + investigator elapsed times."""
    total = investigation_data.get("triage", {}).get("elapsed_s", 0)
    for inv in investigation_data.get("investigators", []):
        total += inv.get("elapsed_s", 0)
    return round(total, 2)
