"""
Seed evaluations, indicator results, and alerts so the dashboard
shows real data instead of zeros.

Creates:
- ~60 historical (already-processed) withdrawals with evaluations
- 8 indicator results per evaluation
- Alerts for escalated/blocked cases
- Mix of approved/escalated/blocked statuses over the past 7 days

Called from seed_data.main() after customers are seeded.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.data.db.models import (
    Alert,
    Customer,
    Evaluation,
    IndicatorResult,
    PaymentMethod,
    Withdrawal,
)

random.seed(99)

NOW = datetime.now(timezone.utc)

INDICATORS = [
    ("amount_anomaly", 1.0),
    ("velocity", 1.0),
    ("payment_method_risk", 1.0),
    ("geographic_risk", 1.2),
    ("device_fingerprint", 1.3),
    ("trading_behavior", 1.5),
    ("recipient_analysis", 1.0),
    ("card_error_history", 1.2),
]

RECIPIENT_NAMES = [
    "Self", "John Doe", "Maria Garcia", "Chen Wei",
    "Priya Sharma", "Ahmed Ali", "Elena Volkov",
]

INVESTIGATOR_NAMES = ["financial_behavior", "identity_access", "cross_account"]

CONSTELLATION_TEMPLATES = {
    "escalated": [
        "Elevated signals across {n} dimensions. The {dim1} indicator shows moderate deviation "
        "while {dim2} presents ambiguous patterns. Account history partially mitigates concern, "
        "but the combination warrants deeper investigation into financial behavior and identity consistency.",
        "Mixed risk constellation: {dim1} and {dim2} show conflicting signals. "
        "The account's trading history is inconsistent with the withdrawal pattern. "
        "Recommend targeted investigation into financial behavior to resolve ambiguity.",
        "Borderline risk pattern detected. {dim1} score elevated but {dim2} within normal range. "
        "The timing and amount of this withdrawal relative to account age raise questions "
        "that require identity verification and financial behavior analysis.",
    ],
    "blocked": [
        "Critical risk constellation: {dim1} and {dim2} both at elevated levels. "
        "Multiple hard fraud signals — minimal trading activity, new account, "
        "and withdrawal amount near deposit total. Cross-account patterns detected "
        "indicating coordinated activity.",
        "High-severity pattern: {dim1} critically elevated, {dim2} confirms suspicion. "
        "Device sharing across accounts, rapid deposit-to-withdrawal cycle, "
        "and geographic inconsistencies form a clear fraud signature.",
        "Cluster of critical indicators: {dim1}, {dim2}, and velocity signals "
        "converge on a high-confidence fraud determination. Account behavior is "
        "inconsistent with legitimate trading — possible account takeover or "
        "deposit-and-run scheme.",
    ],
}

INVESTIGATOR_REASONING = {
    "financial_behavior": {
        "escalated": [
            "Trading volume is below average for the account age. Withdrawal amount "
            "represents a significant portion of total deposits, though not critically so. "
            "Deposit-to-withdrawal ratio of {ratio:.1f} is borderline.",
            "Financial pattern analysis shows irregular timing between deposits and withdrawal "
            "requests. Recent trading activity does not fully justify the withdrawal amount, "
            "but account has some legitimate history.",
        ],
        "blocked": [
            "Severe financial anomaly: deposit-to-withdrawal ratio near 1.0 with minimal "
            "trading activity. Only {trades} trade(s) placed, total volume negligible. "
            "This is a classic deposit-and-run pattern.",
            "Financial behavior is inconsistent with legitimate trading. Near-total withdrawal "
            "of deposited funds with virtually no trading history. Clear money laundering "
            "or stolen card cashout indicators.",
        ],
    },
    "identity_access": {
        "escalated": [
            "Device fingerprint is untrusted but consistent with recent sessions. "
            "IP geolocation shows some variation but no impossible travel. "
            "Account access patterns are somewhat irregular.",
            "Identity signals are mixed: device is relatively new but IP is consistent "
            "with registered country. No VPN detected. Account reactivation after "
            "dormancy period raises moderate concern.",
        ],
        "blocked": [
            "Multiple identity red flags: device shared with another account, "
            "untrusted device status, and IP inconsistency with registration country. "
            "Strong indicators of account being operated by unauthorized party.",
            "Identity verification failed multiple checks: new device appearing from "
            "unexpected location, impossible travel detected between last known location "
            "and current session. High confidence of unauthorized access.",
        ],
    },
    "cross_account": {
        "escalated": [
            "No definitive cross-account links found, but some behavioral similarity "
            "with other recent escalations. Recipient account has not been seen before "
            "in the system. Monitoring recommended.",
            "Weak cross-account signal: withdrawal timing coincides with activity "
            "on other flagged accounts but no direct device or IP overlap confirmed.",
        ],
        "blocked": [
            "Direct cross-account fraud ring detected: device fingerprint shared with "
            "{linked_account}. Same-day withdrawals to identical recipient. "
            "Coordinated extraction pattern across multiple accounts.",
            "Strong cross-account correlation: shared device, overlapping IP addresses, "
            "and matching recipient details with {linked_account}. High-confidence "
            "fraud ring activity.",
        ],
    },
}


def _build_seed_investigation_data(decision: str, comp_score: float) -> dict | None:
    """Generate realistic investigation_data for escalated/blocked evaluations."""
    if decision == "approved":
        return None

    dims = ["velocity", "amount_anomaly", "device_fingerprint",
            "geographic_risk", "trading_behavior", "card_error_history"]
    dim1, dim2 = random.sample(dims, 2)

    constellation = random.choice(CONSTELLATION_TEMPLATES[decision]).format(
        n=random.randint(2, 4), dim1=dim1.replace("_", " "),
        dim2=dim2.replace("_", " "),
    )

    # Pick 2 investigators for escalated, 2-3 for blocked
    num_inv = 2 if decision == "escalated" else random.choice([2, 3])
    chosen = random.sample(INVESTIGATOR_NAMES, num_inv)

    assignments = [
        {"investigator": name, "priority": "high" if decision == "blocked" else "medium"}
        for name in chosen
    ]

    investigators = []
    for name in chosen:
        templates = INVESTIGATOR_REASONING[name][decision]
        reasoning = random.choice(templates).format(
            ratio=round(random.uniform(0.8, 1.0), 1) if decision == "blocked"
            else round(random.uniform(0.5, 0.8), 1),
            trades=random.randint(0, 2),
            linked_account=f"CUST-{random.randint(11, 16):03d}",
        )
        inv_score = round(
            random.uniform(0.55, 0.85) if decision == "blocked"
            else random.uniform(0.30, 0.55), 3,
        )
        investigators.append({
            "name": name,
            "score": inv_score,
            "confidence": round(random.uniform(0.65, 0.95), 3),
            "reasoning": reasoning,
            "elapsed_s": round(random.uniform(4.0, 10.0), 2),
        })

    return {
        "triage": {
            "constellation_analysis": constellation,
            "assignments": assignments,
            "elapsed_s": round(random.uniform(1.5, 4.0), 2),
        },
        "investigators": investigators,
    }


def _random_scores_for_decision(
    decision: str,
) -> list[tuple[str, float, float, str]]:
    """Return (name, score, confidence, reasoning) tuples for 8 indicators."""
    results = []
    for name, weight in INDICATORS:
        if decision == "approved":
            score = round(random.uniform(0.01, 0.25), 3)
        elif decision == "escalated":
            score = round(random.uniform(0.15, 0.55), 3)
        else:  # blocked
            score = round(random.uniform(0.45, 0.95), 3)
        confidence = round(random.uniform(0.7, 1.0), 3)
        reasoning = f"{name.replace('_', ' ').title()} check — score {score:.2f}"
        results.append((name, score, weight, confidence, reasoning))
    return results


def _composite_score(indicators: list) -> float:
    total_w = sum(i[2] for i in indicators)
    weighted = sum(i[1] * i[2] for i in indicators)
    return round(weighted / total_w, 4)


async def seed_dashboard_data(session: AsyncSession) -> int:
    """Create historical evaluations, indicators, and alerts.

    Returns the number of evaluations created.
    """
    # Fetch all customers with their payment methods
    customers = (
        await session.execute(select(Customer))
    ).scalars().all()
    if not customers:
        return 0

    pm_map: dict[uuid.UUID, uuid.UUID] = {}
    pm_rows = (await session.execute(select(PaymentMethod))).scalars().all()
    for pm in pm_rows:
        pm_map.setdefault(pm.customer_id, pm.id)

    eval_count = 0

    # ── Phase 1: Historical withdrawals (already processed) ──
    # Spread over the past 7 days, ~8 per day = ~56 total
    for day_offset in range(7):
        day_base = NOW - timedelta(days=day_offset + 1)
        txns_per_day = random.randint(6, 10)

        for i in range(txns_per_day):
            ts = day_base + timedelta(
                hours=random.randint(8, 22),
                minutes=random.randint(0, 59),
            )
            cust = random.choice(customers)
            pm_id = pm_map.get(cust.id)
            if not pm_id:
                continue

            # Decision distribution: 70% approved, 15% escalated, 15% blocked
            roll = random.random()
            if roll < 0.70:
                decision = "approved"
            elif roll < 0.85:
                decision = "escalated"
            else:
                decision = "blocked"

            amount = Decimal(str(round(random.uniform(50, 8000), 2)))
            recipient = random.choice(RECIPIENT_NAMES)

            w_id = uuid.uuid4()
            e_id = uuid.uuid4()

            session.add(Withdrawal(
                id=w_id,
                customer_id=cust.id,
                amount=amount,
                currency="USD",
                payment_method_id=pm_id,
                recipient_name=recipient,
                recipient_account=f"ACCT-{random.randint(100000, 999999)}",
                ip_address=f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                device_fingerprint=uuid.uuid4().hex[:32],
                location=cust.country,
                status="approved" if decision == "approved" else "pending",
                is_fraud=decision == "blocked",
                requested_at=ts,
                processed_at=ts + timedelta(seconds=random.uniform(0.1, 15)),
                created_at=ts,
            ))

            indicators = _random_scores_for_decision(decision)
            comp_score = _composite_score(indicators)

            risk_level = "low"
            if comp_score >= 0.7:
                risk_level = "high"
            elif comp_score >= 0.3:
                risk_level = "medium"

            elapsed = round(random.uniform(0.1, 14.0), 2)
            if decision == "approved":
                elapsed = round(random.uniform(0.1, 0.5), 2)

            session.add(Evaluation(
                id=e_id,
                withdrawal_id=w_id,
                composite_score=comp_score,
                decision=decision,
                risk_level=risk_level,
                summary=f"{decision.title()} — composite {comp_score:.2f}",
                has_hard_escalation=decision == "blocked",
                has_multi_critical=comp_score >= 0.7,
                gray_zone_used=False,
                investigation_data=_build_seed_investigation_data(decision, comp_score),
                elapsed_s=elapsed,
                checked_at=ts + timedelta(seconds=elapsed),
            ))

            for name, score, weight, confidence, reasoning in indicators:
                session.add(IndicatorResult(
                    id=uuid.uuid4(),
                    withdrawal_id=w_id,
                    evaluation_id=e_id,
                    indicator_name=name,
                    score=score,
                    weight=weight,
                    confidence=confidence,
                    reasoning=reasoning,
                    evidence={"source": "seed", "score": score},
                    created_at=ts,
                ))

            # Alerts for non-approved
            if decision in ("escalated", "blocked"):
                top_inds = sorted(indicators, key=lambda x: x[1], reverse=True)
                session.add(Alert(
                    id=uuid.uuid4(),
                    withdrawal_id=w_id,
                    customer_id=cust.id,
                    alert_type="block" if decision == "blocked" else "escalation",
                    risk_score=comp_score,
                    top_indicators=[t[0] for t in top_inds[:3]],
                    is_read=random.random() < 0.4,  # 40% read
                    created_at=ts,
                ))

            eval_count += 1

    # ── Phase 2: Evaluations for the 16 pending scenario withdrawals ──
    pending_wds = (
        await session.execute(
            select(Withdrawal).where(Withdrawal.status == "pending")
        )
    ).scalars().all()

    for w in pending_wds:
        # Decide based on is_fraud flag
        if w.is_fraud:
            decision = "blocked"
        elif float(w.amount) > 3000:
            decision = "escalated"
        else:
            decision = "approved"

        e_id = uuid.uuid4()
        indicators = _random_scores_for_decision(decision)
        comp_score = _composite_score(indicators)
        elapsed = 0.14 if decision == "approved" else round(random.uniform(8, 14), 2)

        risk_level = "low"
        if comp_score >= 0.7:
            risk_level = "high"
        elif comp_score >= 0.3:
            risk_level = "medium"

        session.add(Evaluation(
            id=e_id,
            withdrawal_id=w.id,
            composite_score=comp_score,
            decision=decision,
            risk_level=risk_level,
            summary=f"{decision.title()} — composite {comp_score:.2f}",
            has_hard_escalation=decision == "blocked",
            has_multi_critical=comp_score >= 0.7,
            gray_zone_used=False,
            investigation_data=_build_seed_investigation_data(decision, comp_score),
            elapsed_s=elapsed,
            checked_at=w.requested_at + timedelta(seconds=elapsed),
        ))

        for name, score, weight, confidence, reasoning in indicators:
            session.add(IndicatorResult(
                id=uuid.uuid4(),
                withdrawal_id=w.id,
                evaluation_id=e_id,
                indicator_name=name,
                score=score,
                weight=weight,
                confidence=confidence,
                reasoning=reasoning,
                evidence={"source": "seed", "score": score},
                created_at=w.requested_at,
            ))

        if decision in ("escalated", "blocked"):
            top_inds = sorted(indicators, key=lambda x: x[1], reverse=True)
            session.add(Alert(
                id=uuid.uuid4(),
                withdrawal_id=w.id,
                customer_id=w.customer_id,
                alert_type="block" if decision == "blocked" else "escalation",
                risk_score=comp_score,
                top_indicators=[t[0] for t in top_inds[:3]],
                is_read=False,
                created_at=w.requested_at,
            ))

        eval_count += 1

    return eval_count
