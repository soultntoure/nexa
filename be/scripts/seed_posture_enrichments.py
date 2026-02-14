"""
Posture-aware seed data enrichments (Phase 0+1, Unit 8).

Adds temporal depth to the existing 16 customers so that posture signals
produce meaningful, differentiable results.  Called from ``seed_data.py``
main() after base seeding, or run standalone after seed_data.py.

## Design Rationale

The base seed_data.py creates customer profiles optimised for the
rule-engine pipeline (indicators).  For posture signals, we need:

  - **Stable baselines** for clean customers so velocity_trends sees
    ``7d / 8-30d`` ratios near 1.0 and funding_behavior sees healthy
    deposit-to-trade ratios.
  - **Signal-specific injections** for escalate customers so exactly one
    or two signals land in the 0.30-0.60 (watch) band.
  - **Amplified fraud patterns** for fraud customers so composite scores
    land above 0.60 (high_risk).

## Enrichment Summary

### Clean (target: posture = normal, composite < 0.30)
  Sarah  - 4 extra deposits spread across lifetime
  James  - 3 extra deposits in the baseline window (8-30d ago)
  Aisha  - 4 extra deposits, 1 extra IP entry at 120d ago
  Kenji  - 3 extra deposits, 1 extra IP entry at 45d ago
  Emma   - 5 extra deposits, 10 extra trades, 1 extra IP entry at 400d ago
  Raj    - 3 extra deposits, 1 extra IP entry at 200d ago

### Escalate (target: posture = watch, 0.30 <= composite < 0.60)
  David  - 4 more IPs (SGP, VPN DEU, THA, VPN BRA) + 3 rapid VPN deposits
  Maria  - 3 rapid deposits in last 72h + 1 failed tx + 1 unverified e-wallet
  Tom    - 3 failed crypto txns + 2 rapid deposits
  Yuki   - 5 extra pre-dormancy trades + 3 pre-dormancy deposits + 3 return deposits

### Fraud (target: posture = high_risk, composite >= 0.60)
  Victor     - 3 rapid deposits ($6k total) + fraud ring shared IP
  Sophie     - 2 extra failed card attempts + 2 rapid deposits via VPN + VPN IP
  Ahmed      - 3 coordinated deposits within min of Fatima + 2nd shared IP
  Fatima     - 3 coordinated deposits within min of Ahmed + 2nd shared IP
  Carlos     - 2 extra deposits via VPN + 1 extra VPN IP entry
  Nina       - 3 deposits from Sao Paulo IP + VPN IP entry

Run standalone:  python -m scripts.seed_posture_enrichments
Called from:     scripts/seed_data.py  main()
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import (
    IPHistory,
    PaymentMethod,
    Trade,
    Transaction,
)

# ── Shared constants ──
# Use current time so temporal windows align with DB NOW().
NOW = datetime.now(timezone.utc)
FP_FRAUD_RING = "deadbeefdeadbeefdeadbeefdeadbeef"
IP_FRAUD_RING = "41.44.55.66"


def _ago(**kw: float) -> datetime:
    return NOW - timedelta(**kw)


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"deriv.seed.{name}")


# ═══════════════════════════════════════════════════════════════════════════
# CLEAN CUSTOMERS - strengthen baselines so posture = normal
# ═══════════════════════════════════════════════════════════════════════════


async def _enrich_sarah(s: AsyncSession) -> None:
    """Sarah Chen - add 4 deposits spread across lifetime.

    Existing: 15 deposits (500d-7d), 4 IP entries (400d, 200d, 30d, 1d).
    Add deposits at 25d, 18d (baseline window) and 120d, 300d (lifetime)
    so velocity_trends sees stable activity.

    Posture signals affected:
      velocity_trends   - stable baseline prevents false spike
      funding_behavior  - more deposits improves deposit-to-trade ratio
    """
    cid = _id("sarah")
    pm = _id("sarah.pm.visa")
    ip = "51.148.20.30"

    deposits = [
        (_ago(days=25), Decimal("750.00")),   # baseline window (8-30d)
        (_ago(days=18), Decimal("600.00")),   # baseline window
        (_ago(days=120), Decimal("1100.00")), # mid-lifetime
        (_ago(days=300), Decimal("900.00")),  # early-lifetime
    ]
    for ts, amount in deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))


async def _enrich_james(s: AsyncSession) -> None:
    """James Wilson - add 3 deposits in baseline window.

    Existing: 20 deposits (1000d-5d), 4 IP entries (800d, 300d, 30d, 1d).
    Already very strong profile.  Deposits in baseline window ensure
    velocity_trends ratio stays near 1.0.

    Posture signals affected:
      velocity_trends   - reinforced baseline
    """
    cid = _id("james")
    pm = _id("james.pm.bank")
    ip = "72.229.30.40"

    deposits = [
        (_ago(days=22), Decimal("8000.00")),  # baseline window
        (_ago(days=15), Decimal("12000.00")), # baseline window
        (_ago(days=10), Decimal("6500.00")),  # baseline window
    ]
    for ts, amount in deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))


async def _enrich_aisha(s: AsyncSession) -> None:
    """Aisha Mohammed - add 4 deposits + 1 IP entry.

    Existing: 8 deposits (220d-10d), 3 IPs (200d, 60d, 7d).
    Add deposits in baseline window and an older IP entry so
    infrastructure_stability sees >30d spacing.

    Posture signals affected:
      velocity_trends            - reinforced baseline
      infrastructure_stability   - older IP entry shows stability
      funding_behavior           - more deposits improves ratio
    """
    cid = _id("aisha")
    pm = _id("aisha.pm.skrill")
    ip = "94.56.78.90"

    deposits = [
        (_ago(days=25), Decimal("400.00")),  # baseline window
        (_ago(days=16), Decimal("550.00")),  # baseline window
        (_ago(days=150), Decimal("350.00")), # mid-lifetime
        (_ago(days=90), Decimal("600.00")),  # mid-lifetime
    ]
    for ts, amount in deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))

    # Extra IP entry to ensure >30d spacing
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Dubai, ARE",
        first_seen_at=_ago(days=120), last_seen_at=_ago(days=120),
        created_at=_ago(days=120),
    ))


async def _enrich_kenji(s: AsyncSession) -> None:
    """Kenji Sato - add 3 deposits + 1 IP entry.

    Existing: 12 deposits (350d-5d), 3 IPs (300d, 100d, 5d).
    Latest IP at 5d is fine but adding one at 45d ago strengthens
    the 30d-window stability picture.

    Posture signals affected:
      velocity_trends            - reinforced baseline
      infrastructure_stability   - additional IP in 30d window (same location)
    """
    cid = _id("kenji")
    pm = _id("kenji.pm.btc")
    ip = "103.5.140.50"

    deposits = [
        (_ago(days=20), Decimal("1200.00")), # baseline window
        (_ago(days=14), Decimal("800.00")),  # baseline window
        (_ago(days=180), Decimal("1500.00")),# mid-lifetime
    ]
    for ts, amount in deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))

    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Tokyo, JPN",
        first_seen_at=_ago(days=45), last_seen_at=_ago(days=45),
        created_at=_ago(days=45),
    ))


async def _enrich_emma(s: AsyncSession) -> None:
    """Emma Davies - add 5 deposits + 10 trades + 1 IP entry.

    Existing: 6 deposits (700d-30d), 25 trades, 3 IPs (600d, 180d, 10d).
    Low trade count (25) risks account_maturity scoring her as low-density.
    Add trades and deposits to strengthen baselines. Add IP at 400d ago
    for better temporal spread.

    Posture signals affected:
      account_maturity  - more trades improves density score
      velocity_trends   - baseline-window deposits prevent spike
      funding_behavior  - more deposits and trades improve ratio
    """
    cid = _id("emma")
    pm = _id("emma.pm.visa")
    ip = "51.148.88.12"

    deposits = [
        (_ago(days=22), Decimal("200.00")),  # baseline window
        (_ago(days=15), Decimal("180.00")),  # baseline window
        (_ago(days=500), Decimal("300.00")), # early-lifetime
        (_ago(days=350), Decimal("250.00")), # mid-lifetime
        (_ago(days=100), Decimal("150.00")), # recent-lifetime
    ]
    for ts, amount in deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="GBP", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))

    # 10 extra trades spread across last 180 days to boost density
    span_start = _ago(days=160)
    span_end = _ago(days=10)
    span_secs = (span_end - span_start).total_seconds()
    for i in range(10):
        opened = span_start + timedelta(seconds=span_secs * i / 10)
        closed = opened + timedelta(seconds=3600)
        s.add(Trade(
            id=uuid.uuid4(), customer_id=cid,
            instrument="GBP/USD", trade_type="buy",
            amount=Decimal("80.00"), pnl=Decimal("5.20"),
            opened_at=opened, closed_at=closed, created_at=opened,
        ))

    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Manchester, GBR",
        first_seen_at=_ago(days=400), last_seen_at=_ago(days=400),
        created_at=_ago(days=400),
    ))


async def _enrich_raj(s: AsyncSession) -> None:
    """Raj Patel - add 3 deposits + 1 IP entry.

    Existing: 18 deposits (350d-3d), 120 trades, 3 IPs (300d, 90d, 3d).
    Already strong.  Add deposits in baseline window and an IP entry
    at 200d for better temporal spread.

    Posture signals affected:
      velocity_trends   - reinforced baseline
    """
    cid = _id("raj")
    pm = _id("raj.pm.bank")
    ip = "49.36.120.80"

    deposits = [
        (_ago(days=24), Decimal("2500.00")), # baseline window
        (_ago(days=12), Decimal("3500.00")), # baseline window
        (_ago(days=200), Decimal("4000.00")),# mid-lifetime
    ]
    for ts, amount in deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))

    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Mumbai, IND",
        first_seen_at=_ago(days=200), last_seen_at=_ago(days=200),
        created_at=_ago(days=200),
    ))


# ═══════════════════════════════════════════════════════════════════════════
# ESCALATE CUSTOMERS - targeted signal injections for posture = watch
# ═══════════════════════════════════════════════════════════════════════════


async def _enrich_david(s: AsyncSession) -> None:
    """David Park - strengthen infrastructure_stability + velocity signals.

    Existing: 5 IP entries (Seoul, Tokyo, New York, Seoul, VPN NLD).
    Add 4 IPs (SGP, VPN DEU, THA, VPN BRA) in last 30d
    + 3 rapid deposits via VPN in last 72h for velocity spike.

    Posture signals affected:
      infrastructure_stability - distinct_countries increases in 30d
                                 vpn_ratio: 1/5 -> 3/9 = 0.33
      velocity_trends          - 3 deposits in 7d with weak baseline
    """
    cid = _id("david")
    pm = _id("david.pm.visa")

    new_ips = [
        (_ago(days=20), "13.215.40.50", "Singapore, SGP", False),
        (_ago(days=14), "45.12.100.88", "VPN Exit, DEU", True),
        (_ago(days=8), "202.79.33.10", "Bangkok, THA", False),
        (_ago(days=3), "104.28.55.12", "VPN Exit, BRA", True),
    ]
    for dt, ip, loc, vpn in new_ips:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location=loc, is_vpn=vpn,
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))

    # Rapid deposits via VPN - velocity spike
    for hours_ago, amount in [(60, "3000.00"), (30, "2500.00"), (6, "4000.00")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal(amount), currency="USD", status="success",
            payment_method_id=pm, ip_address="45.12.100.88",
            timestamp=_ago(hours=hours_ago), created_at=_ago(hours=hours_ago),
        ))


async def _enrich_maria(s: AsyncSession) -> None:
    """Maria Santos - strengthen velocity_trends + payment_risk signals.

    Existing: 3 deposits (18d-3d), 1 bank transfer added 2d ago.
    Add 3 rapid deposits in last 72h (velocity spike vs her 3-week baseline),
    1 failed tx (declined) at 3h ago, and 1 unverified e-wallet added 1d ago.

    Posture signals affected:
      velocity_trends - 3 deposits in 7d vs ~0 in 8-30d baseline
      payment_risk    - failed tx + unverified method, newest method age = 1d
    """
    cid = _id("maria")
    pm_bank = _id("maria.pm.bank")
    pm_ewallet = _id("maria.pm.ewallet")
    ip = "177.71.200.30"

    # Three rapid deposits in last 72h - strong velocity spike
    rapid_deposits = [
        (_ago(hours=60), Decimal("4000.00")),
        (_ago(hours=36), Decimal("3500.00")),
        (_ago(hours=6), Decimal("5000.00")),
    ]
    for ts, amount in rapid_deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm_bank, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))

    # Failed tx on bank method - boosts payment_risk further
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid, type="deposit",
        amount=Decimal("2000.00"), currency="USD", status="failed",
        payment_method_id=pm_bank, error_code="declined",
        ip_address=ip,
        timestamp=_ago(hours=3), created_at=_ago(hours=3),
    ))

    # New unverified e-wallet - boosts payment_risk
    s.add(PaymentMethod(
        id=pm_ewallet, customer_id=cid, type="ewallet", provider="neteller",
        is_verified=False, added_at=_ago(days=1),
        last_used_at=None, created_at=_ago(days=1),
    ))


async def _enrich_tom(s: AsyncSession) -> None:
    """Tom Brown - add 3 failed crypto txns + 2 rapid deposits.

    Existing: old Visa (verified, 360d) + new BTC wallet (verified, 1d).
    3 failed txns (crypto_timeout, insufficient_funds) push payment_risk's
    failed_tx_rate well above 0%. 2 rapid deposits create velocity spike.

    Posture signals affected:
      payment_risk    - failed_tx_rate: 3 failed in 30d window
      velocity_trends - 2 deposits in 48h vs weak baseline
    """
    cid = _id("tom")
    pm_new = _id("tom.pm.btc")
    ip = "203.206.50.10"

    # 3 failed txns on new method - strong payment_risk signal
    for hours_ago, err in [(18, "crypto_timeout"), (12, "insufficient_funds"), (4, "crypto_timeout")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("500.00"), currency="AUD", status="failed",
            payment_method_id=pm_new, error_code=err,
            ip_address=ip,
            timestamp=_ago(hours=hours_ago), created_at=_ago(hours=hours_ago),
        ))

    # 2 rapid deposits - velocity spike
    for hours_ago, amount in [(48, "800.00"), (8, "1200.00")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal(amount), currency="AUD", status="success",
            payment_method_id=pm_new, ip_address=ip,
            timestamp=_ago(hours=hours_ago), created_at=_ago(hours=hours_ago),
        ))


async def _enrich_yuki(s: AsyncSession) -> None:
    """Yuki Tanaka - strengthen dormancy gap + return-activity signals.

    Existing: 8 deposits (700d-200d), 40 pre-dormancy trades, 3 post-return
    trades, 4 past WDs.  6-month dormancy gap (200d-5d).

    Add 5 more pre-dormancy trades + 3 pre-dormancy deposits to create a
    strong baseline, then add 3 return deposits (5d, 3d, 1d ago) to show
    post-dormancy velocity spike.

    Posture signals affected:
      account_maturity - dormancy gap stays visible (180d), baseline
                         trade count is now higher making the gap starker
      velocity_trends  - 3 return deposits create spike vs zero baseline
                         in the 8-30d window (no activity from 200d to 5d)
      funding_behavior - return deposits with few trades shows imbalance
    """
    cid = _id("yuki")
    pm = _id("yuki.pm.visa")
    ip = "103.5.140.70"

    # 5 extra pre-dormancy trades (700d-210d range, before the gap)
    pre_dorm_start = _ago(days=650)
    pre_dorm_end = _ago(days=210)
    span = (pre_dorm_end - pre_dorm_start).total_seconds()
    for i in range(5):
        opened = pre_dorm_start + timedelta(seconds=span * i / 5)
        closed = opened + timedelta(seconds=7200)
        s.add(Trade(
            id=uuid.uuid4(), customer_id=cid,
            instrument="USD/JPY", trade_type="sell",
            amount=Decimal("300.00"), pnl=Decimal("15.50"),
            opened_at=opened, closed_at=closed, created_at=opened,
        ))

    # 3 extra pre-dormancy deposits (strengthen the "was active" baseline)
    pre_deposits = [
        (_ago(days=600), Decimal("800.00")),
        (_ago(days=450), Decimal("1200.00")),
        (_ago(days=250), Decimal("600.00")),
    ]
    for ts, amount in pre_deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=ts, created_at=ts,
        ))

    # 3 return deposits in last 5 days - velocity spike after dormancy
    for days_ago, amount in [(5, "1500.00"), (3, "2000.00"), (1, "1800.00")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal(amount), currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=_ago(days=days_ago), created_at=_ago(days=days_ago),
        ))


# ═══════════════════════════════════════════════════════════════════════════
# FRAUD CUSTOMERS - amplify signals for posture = high_risk
# ═══════════════════════════════════════════════════════════════════════════


async def _enrich_victor(s: AsyncSession) -> None:
    """Victor Petrov - add 3 rapid deposits + fraud ring shared IP.

    Existing: single $3,000 deposit at 3d ago, 1 tiny trade, 5d account.
    Adding 3 deposits ($2k + $1.5k + $2.5k = $6k) creates:
      - velocity spike (4 deposits in 7d, 0 in 8-30d baseline)
      - $9,000 total deposits vs $10 trading → deposit-to-trade ratio = 900:1
    Adding shared fraud ring IP strengthens graph_proximity signal.

    Posture signals affected:
      velocity_trends  - zero-baseline edge case, strong spike
      funding_behavior - deposit-to-trade ratio: 900:1 (extreme)
      graph_proximity  - shared IP with fraud ring (Ahmed/Fatima)
    """
    cid = _id("victor")
    pm = _id("victor.pm.visa")
    ip = "95.173.120.45"

    # 3 rapid deposits - strong velocity spike against zero baseline
    for days_ago, amount in [(3, "2000.00"), (2, "1500.00"), (1, "2500.00")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal(amount), currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=_ago(days=days_ago), created_at=_ago(days=days_ago),
        ))

    # Shared IP with fraud ring - graph proximity boost
    s.add(IPHistory(
        customer_id=cid, ip_address=IP_FRAUD_RING,
        location="Cairo, EGY",
        first_seen_at=_ago(days=2), last_seen_at=_ago(days=1),
        created_at=_ago(days=2),
    ))


async def _enrich_sophie(s: AsyncSession) -> None:
    """Sophie Laurent - add 2 failed card attempts + 2 VPN deposits + VPN IP.

    Existing: 3 failed deposits (card_restricted) + 1 success.
    Add 2 more failed attempts (insufficient_funds, card_restricted) to boost
    payment_risk. Add 2 rapid deposits via VPN IP for velocity spike and
    infrastructure instability. Add VPN IP entry.

    Posture signals affected:
      payment_risk               - failed_tx_rate increases significantly
      velocity_trends            - 2 rapid deposits via new IP
      infrastructure_stability   - VPN IP entry adds instability
    """
    cid = _id("sophie")
    pm_bad3 = _id("sophie.pm.bad3")
    ip = "88.160.45.78"

    # 2 more failed card attempts - boost payment_risk further
    for hours_ago, err in [(36, "insufficient_funds"), (8, "card_restricted")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("500.00"), currency="USD", status="failed",
            payment_method_id=pm_bad3, error_code=err,
            ip_address=ip,
            timestamp=_ago(hours=hours_ago), created_at=_ago(hours=hours_ago),
        ))

    # 2 rapid deposits via different IP - velocity spike + infra instability
    vpn_ip = "185.199.108.77"
    for hours_ago, amount in [(24, "3000.00"), (4, "2000.00")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal(amount), currency="USD", status="success",
            payment_method_id=pm_bad3, ip_address=vpn_ip,
            timestamp=_ago(hours=hours_ago), created_at=_ago(hours=hours_ago),
        ))

    # VPN IP entry for infra instability
    s.add(IPHistory(
        customer_id=cid, ip_address=vpn_ip,
        location="VPN Exit, NLD", is_vpn=True,
        first_seen_at=_ago(days=1), last_seen_at=_ago(hours=4),
        created_at=_ago(days=1),
    ))


async def _enrich_ahmed_and_fatima(s: AsyncSession) -> None:
    """Ahmed + Fatima - add 3 coordinated deposit pairs + 2nd shared IP entry.

    Existing: Ahmed has 1 deposit ($2k), Fatima has 1 deposit ($1.5k).
    Both share device fingerprint + IP + recipient.

    Add 3 deposits each, timed within minutes of each other (coordinated
    timing at 3d, 2d, and 8h ago), and a second shared IP entry from 4d
    ago to strengthen graph_proximity evidence.

    Posture signals affected:
      graph_proximity  - 2nd shared IP entry (2 dates, not just 1)
      funding_behavior - more deposits with no/minimal trading
      velocity_trends  - multiple deposits in 7d with zero-baseline
    """
    cid_a = _id("ahmed")
    pm_a = _id("ahmed.pm.visa")
    cid_f = _id("fatima")
    pm_f = _id("fatima.pm.visa")

    # Coordinated deposits: Ahmed, then Fatima 8 min later, 3 rounds
    ahmed_deposits = [
        (_ago(days=3, hours=2), Decimal("1000.00")),
        (_ago(days=2, hours=5), Decimal("800.00")),
        (_ago(hours=8), Decimal("1200.00")),
    ]
    fatima_deposits = [
        (_ago(days=3, hours=2, minutes=8), Decimal("900.00")),
        (_ago(days=2, hours=5, minutes=6), Decimal("700.00")),
        (_ago(hours=8, minutes=5), Decimal("1100.00")),
    ]

    for ts, amount in ahmed_deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid_a, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm_a, ip_address=IP_FRAUD_RING,
            timestamp=ts, created_at=ts,
        ))
    for ts, amount in fatima_deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid_f, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm_f, ip_address=IP_FRAUD_RING,
            timestamp=ts, created_at=ts,
        ))

    # Second shared IP entry from a different date (strengthens graph_proximity)
    shared_ip_date = _ago(days=4)
    s.add(IPHistory(
        customer_id=cid_a, ip_address=IP_FRAUD_RING,
        location="Cairo, EGY",
        first_seen_at=shared_ip_date, last_seen_at=shared_ip_date,
        created_at=shared_ip_date,
    ))
    s.add(IPHistory(
        customer_id=cid_f, ip_address=IP_FRAUD_RING,
        location="Cairo, EGY",
        first_seen_at=shared_ip_date, last_seen_at=shared_ip_date,
        created_at=shared_ip_date,
    ))


async def _enrich_carlos(s: AsyncSession) -> None:
    """Carlos Mendez - add 2 VPN deposits + 1 extra VPN IP entry.

    Existing: 5 deposits (80d-10d from MEX IP), 20 trades, 3 devices,
    5 pending WDs via VPN. Has 2 IPs (MEX + VPN USA).

    Add deposits through VPN to strengthen velocity_trends (recent activity
    vs baseline) and an additional VPN IP for infrastructure_stability.

    Posture signals affected:
      velocity_trends            - recent VPN deposits spike vs baseline
      infrastructure_stability   - vpn_ratio increases: 2/3 entries via VPN
      funding_behavior           - total deposits increase relative to trades
    """
    cid = _id("carlos")
    pm = _id("carlos.pm.visa")
    vpn_ip = "185.199.108.55"
    vpn_ip2 = "185.199.108.99"

    # Deposits via VPN in last 7 days
    vpn_deposits = [
        (_ago(days=3), Decimal("1500.00")),
        (_ago(days=1), Decimal("2000.00")),
    ]
    for ts, amount in vpn_deposits:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=amount, currency="USD", status="success",
            payment_method_id=pm, ip_address=vpn_ip,
            timestamp=ts, created_at=ts,
        ))

    # Additional VPN IP entry from different exit node
    s.add(IPHistory(
        customer_id=cid, ip_address=vpn_ip2,
        location="VPN Exit, CAN", is_vpn=True,
        first_seen_at=_ago(days=1), last_seen_at=_ago(hours=3),
        created_at=_ago(days=1),
    ))


async def _enrich_nina(s: AsyncSession) -> None:
    """Nina Volkov - add 3 deposits from Sao Paulo IP + VPN IP entry.

    Existing: 3 deposits (25d-5d from Kyiv IP), 8 trades, 2 IPs (Kyiv, SP),
    2 devices (orig, new).

    Add 3 deposits from Sao Paulo IP in last 72h to reinforce the
    impossible-travel signal with velocity spike. Add VPN IP entry
    for additional infrastructure instability.

    Posture signals affected:
      infrastructure_stability - VPN IP + distinct_countries in 30d
      velocity_trends          - 3 recent deposits create spike
    """
    cid = _id("nina")
    pm = _id("nina.pm.visa")
    ip_saopaulo = "177.71.88.99"

    # 3 deposits from anomalous location in last 72h - velocity spike + infra
    for hours_ago, amount in [(60, "1000.00"), (24, "1500.00"), (4, "2000.00")]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal(amount), currency="USD", status="success",
            payment_method_id=pm, ip_address=ip_saopaulo,
            timestamp=_ago(hours=hours_ago), created_at=_ago(hours=hours_ago),
        ))

    # VPN IP entry - infra instability
    s.add(IPHistory(
        customer_id=cid, ip_address="104.28.33.77",
        location="VPN Exit, USA", is_vpn=True,
        first_seen_at=_ago(days=2), last_seen_at=_ago(hours=6),
        created_at=_ago(days=2),
    ))


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API - called from seed_data.py or run standalone
# ═══════════════════════════════════════════════════════════════════════════

ENRICHMENT_SEEDERS = [
    # Clean (target: posture = normal)
    ("Sarah Chen - baseline deposits", _enrich_sarah),
    ("James Wilson - baseline deposits", _enrich_james),
    ("Aisha Mohammed - baseline deposits + IP", _enrich_aisha),
    ("Kenji Sato - baseline deposits + IP", _enrich_kenji),
    ("Emma Davies - deposits + trades + IP", _enrich_emma),
    ("Raj Patel - baseline deposits + IP", _enrich_raj),
    # Escalate (target: posture = watch)
    ("David Park - extra IPs + VPN", _enrich_david),
    ("Maria Santos - velocity spike + unverified method", _enrich_maria),
    ("Tom Brown - failed crypto tx", _enrich_tom),
    ("Yuki Tanaka - dormancy depth + return deposit", _enrich_yuki),
    # Fraud (target: posture = high_risk)
    ("Victor Petrov - rapid second deposit", _enrich_victor),
    ("Sophie Laurent - extra failed card attempt", _enrich_sophie),
    ("Ahmed + Fatima - coordinated deposits + 2nd shared IP", _enrich_ahmed_and_fatima),
    ("Carlos Mendez - VPN deposits + extra VPN IP", _enrich_carlos),
    ("Nina Volkov - Sao Paulo deposit", _enrich_nina),
]


async def seed_posture_enrichments(session: AsyncSession) -> int:
    """Run all posture enrichment seeders.  Returns count of enrichments applied."""
    for name, seeder in ENRICHMENT_SEEDERS:
        await seeder(session)
        print(f"  Enriched: {name}")
    return len(ENRICHMENT_SEEDERS)


async def main() -> None:
    """Standalone entrypoint - run after seed_data.py."""
    from app.data.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        count = await seed_posture_enrichments(session)
        await session.commit()
        print(f"\nDone - {count} posture enrichments applied.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
