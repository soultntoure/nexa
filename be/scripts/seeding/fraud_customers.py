"""Fraud customer seeders (5) — expected outcome: BLOCK."""

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import (
    Customer, Device, IPHistory, PaymentMethod, Trade, Transaction, Withdrawal,
)

from .constants import (
    FP_FRAUD_RING, FP_SHARED_FRAUD, IP_FRAUD_RING, NOW, _ago, _id,
)
from .generators import _gen_deposits, _gen_past_withdrawals, _gen_trades


async def _seed_victor(s: AsyncSession) -> None:
    """Victor Petrov — The No-Trade Fraudster.

    5-day account, RUS. Deposited $3,000 via card. ONE tiny trade ($10, 15s).
    Now requests $2,990 withdrawal (>99% of deposits).
    Classic "no trade" fraud pattern (no_trade_withdrawal).
    Uses SHARED device fingerprint with Sophie (FP_SHARED_FRAUD).
    """
    cid, pm, dev = _id("victor"), _id("victor.pm.visa"), _id("victor.device")
    ip = "95.173.120.45"

    s.add(Customer(
        id=cid, external_id="CUST-011", name="Victor Petrov",
        email="victor.petrov@example.com", country="RUS",
        registration_date=_ago(days=5), created_at=_ago(days=5), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="1111", is_verified=True, added_at=_ago(days=5),
        last_used_at=_ago(days=3), created_at=_ago(days=5),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=FP_SHARED_FRAUD,
        os="Windows 10", browser="Chrome 119", screen_resolution="1366x768",
        first_seen_at=_ago(days=5), last_seen_at=_ago(hours=1),
        is_trusted=False, created_at=_ago(days=5),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Moscow, RUS",
        first_seen_at=_ago(days=5), last_seen_at=_ago(hours=1), created_at=_ago(days=5),
    ))
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid, type="deposit",
        amount=Decimal("3000.00"), currency="USD", status="success",
        payment_method_id=pm, ip_address=ip,
        timestamp=_ago(days=3), created_at=_ago(days=3),
    ))
    s.add(Trade(
        id=uuid.uuid4(), customer_id=cid, instrument="EUR/USD",
        trade_type="buy", amount=Decimal("10.00"), pnl=Decimal("0.02"),
        opened_at=_ago(days=2, hours=12),
        closed_at=_ago(days=2, hours=12) + timedelta(seconds=15),
        created_at=_ago(days=2, hours=12),
    ))
    s.add(Withdrawal(
        id=_id("victor.wd.pending"), customer_id=cid, amount=Decimal("2990.00"),
        currency="USD", payment_method_id=pm, recipient_name="Victor Petrov",
        recipient_account="RU0123456789012345678901234", ip_address=ip,
        device_fingerprint=FP_SHARED_FRAUD, location="Moscow, RUS",
        status="pending", is_fraud=True,
        fraud_notes=(
            "No-trade fraud: deposited $3k, placed 1 token trade ($10, 15s), "
            "now withdrawing $2990 (>99% of deposits). "
            "Device shared with CUST-012 (Sophie Laurent). "
            "Account only 5 days old."
        ),
        requested_at=_ago(days=1), created_at=_ago(days=1),
    ))


async def _seed_sophie(s: AsyncSession) -> None:
    """Sophie Laurent — The Card Tester."""
    cid = _id("sophie")
    pm_bad1, pm_bad2, pm_bad3 = (
        _id("sophie.pm.bad1"), _id("sophie.pm.bad2"), _id("sophie.pm.bad3"),
    )
    pm_good = _id("sophie.pm.good")
    dev = _id("sophie.device")
    ip = "88.160.45.78"

    s.add(Customer(
        id=cid, external_id="CUST-012", name="Sophie Laurent",
        email="sophie.laurent@example.com", country="FRA",
        registration_date=_ago(days=14), created_at=_ago(days=14), updated_at=NOW,
    ))
    for i, (pm_id, last4) in enumerate([
        (pm_bad1, "0001"), (pm_bad2, "0002"), (pm_bad3, "0003"),
    ]):
        s.add(PaymentMethod(
            id=pm_id, customer_id=cid, type="card", provider="visa",
            last_four=last4, is_verified=False, is_blacklisted=True,
            added_at=_ago(days=14 - i), last_used_at=_ago(days=12 - i),
            created_at=_ago(days=14 - i),
        ))
    s.add(PaymentMethod(
        id=pm_good, customer_id=cid, type="card", provider="visa",
        last_four="1111", is_verified=True,
        added_at=_ago(days=10), last_used_at=_ago(days=8), created_at=_ago(days=10),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=FP_SHARED_FRAUD,
        os="Windows 10", browser="Chrome 119", screen_resolution="1366x768",
        first_seen_at=_ago(days=14), last_seen_at=_ago(hours=3),
        is_trusted=False, created_at=_ago(days=14),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Paris, FRA",
        first_seen_at=_ago(days=14), last_seen_at=_ago(hours=3), created_at=_ago(days=14),
    ))
    for i, pm_id in enumerate([pm_bad1, pm_bad2, pm_bad3]):
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("500.00"), currency="USD", status="failed",
            payment_method_id=pm_id, error_code="card_restricted", ip_address=ip,
            timestamp=_ago(days=12 - i), created_at=_ago(days=12 - i),
        ))
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid, type="deposit",
        amount=Decimal("500.00"), currency="USD", status="success",
        payment_method_id=pm_good, ip_address=ip,
        timestamp=_ago(days=8), created_at=_ago(days=8),
    ))
    for offset_h in [0, 2]:
        s.add(Trade(
            id=uuid.uuid4(), customer_id=cid, instrument="EUR/USD",
            trade_type="buy", amount=Decimal("5.00"), pnl=Decimal("-0.10"),
            opened_at=_ago(days=7, hours=offset_h),
            closed_at=_ago(days=7, hours=offset_h) + timedelta(seconds=30),
            created_at=_ago(days=7, hours=offset_h),
        ))
    s.add(Withdrawal(
        id=_id("sophie.wd.pending"), customer_id=cid, amount=Decimal("480.00"),
        currency="USD", payment_method_id=pm_good, recipient_name="Sophie Laurent",
        recipient_account="FR7630006000011234567890189", ip_address=ip,
        device_fingerprint=FP_SHARED_FRAUD, location="Paris, FRA",
        status="pending", is_fraud=True,
        fraud_notes=(
            "Card testing pattern: 3 cards failed (card_restricted) before 4th "
            "succeeded. Minimal trading (2 trades, $5 each, 30s duration). "
            "Device shared with CUST-011 (Victor Petrov). Withdrawing 96% of deposit."
        ),
        requested_at=_ago(days=7), created_at=_ago(days=7),
    ))


async def _seed_ahmed_and_fatima(s: AsyncSession) -> None:
    """Ahmed Hassan & Fatima Nour — The Fraud Ring."""
    # ── Ahmed ──
    cid_a, pm_a, dev_a = _id("ahmed"), _id("ahmed.pm.visa"), _id("ahmed.device")

    s.add(Customer(
        id=cid_a, external_id="CUST-013", name="Ahmed Hassan",
        email="ahmed.hassan@example.com", country="EGY",
        registration_date=_ago(days=7), created_at=_ago(days=7), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm_a, customer_id=cid_a, type="card", provider="visa",
        last_four="4444", is_verified=True, added_at=_ago(days=7),
        last_used_at=_ago(days=5), created_at=_ago(days=7),
    ))
    s.add(Device(
        id=dev_a, customer_id=cid_a, fingerprint=FP_FRAUD_RING,
        os="Android 13", browser="Chrome Mobile 120", screen_resolution="1080x2340",
        first_seen_at=_ago(days=7), last_seen_at=_ago(hours=2),
        is_trusted=False, created_at=_ago(days=7),
    ))
    s.add(IPHistory(
        customer_id=cid_a, ip_address=IP_FRAUD_RING, location="Cairo, EGY",
        first_seen_at=_ago(days=7), last_seen_at=_ago(hours=2), created_at=_ago(days=7),
    ))
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid_a, type="deposit",
        amount=Decimal("2000.00"), currency="USD", status="success",
        payment_method_id=pm_a, ip_address=IP_FRAUD_RING,
        timestamp=_ago(days=5), created_at=_ago(days=5),
    ))
    s.add(Trade(
        id=uuid.uuid4(), customer_id=cid_a, instrument="GBP/USD",
        trade_type="buy", amount=Decimal("20.00"), pnl=Decimal("0.50"),
        opened_at=_ago(days=4), closed_at=_ago(days=4) + timedelta(seconds=45),
        created_at=_ago(days=4),
    ))
    # Ahmed withdraws 8 minutes ago (coordinated timing with Fatima)
    s.add(Withdrawal(
        id=_id("ahmed.wd.pending"), customer_id=cid_a, amount=Decimal("1950.00"),
        currency="USD", payment_method_id=pm_a, recipient_name="Mohamed Nour",
        recipient_account="EG800002000156789012345678901",
        ip_address=IP_FRAUD_RING, device_fingerprint=FP_FRAUD_RING,
        location="Cairo, EGY", status="pending", is_fraud=True,
        fraud_notes=(
            "Fraud ring: shares device, IP, and recipient account with CUST-014 "
            "(Fatima Nour). 1-week account, single deposit, 1 token trade (45s), "
            "withdrawing to third-party 'Mohamed Nour'. "
            "Withdrawal within 10 min of Fatima's (coordinated timing)."
        ),
        requested_at=_ago(days=3, minutes=8), created_at=_ago(days=3, minutes=8),
    ))

    # ── Fatima ──
    cid_f, pm_f, dev_f = _id("fatima"), _id("fatima.pm.visa"), _id("fatima.device")

    s.add(Customer(
        id=cid_f, external_id="CUST-014", name="Fatima Nour",
        email="fatima.nour@example.com", country="EGY",
        registration_date=_ago(days=7), created_at=_ago(days=7), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm_f, customer_id=cid_f, type="card", provider="visa",
        last_four="4444", is_verified=True, added_at=_ago(days=7),
        last_used_at=_ago(days=4), created_at=_ago(days=7),
    ))
    s.add(Device(
        id=dev_f, customer_id=cid_f, fingerprint=FP_FRAUD_RING,
        os="Android 13", browser="Chrome Mobile 120", screen_resolution="1080x2340",
        first_seen_at=_ago(days=7), last_seen_at=_ago(hours=1),
        is_trusted=False, created_at=_ago(days=7),
    ))
    s.add(IPHistory(
        customer_id=cid_f, ip_address=IP_FRAUD_RING, location="Cairo, EGY",
        first_seen_at=_ago(days=7), last_seen_at=_ago(hours=1), created_at=_ago(days=7),
    ))
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid_f, type="deposit",
        amount=Decimal("1500.00"), currency="USD", status="success",
        payment_method_id=pm_f, ip_address=IP_FRAUD_RING,
        timestamp=_ago(days=4), created_at=_ago(days=4),
    ))
    # Zero trades for Fatima — even worse signal
    # Fatima withdraws 2 minutes ago (coordinated timing with Ahmed — 6 min gap)
    s.add(Withdrawal(
        id=_id("fatima.wd.pending"), customer_id=cid_f, amount=Decimal("1480.00"),
        currency="USD", payment_method_id=pm_f, recipient_name="Mohamed Nour",
        recipient_account="EG800002000156789012345678901",
        ip_address=IP_FRAUD_RING, device_fingerprint=FP_FRAUD_RING,
        location="Cairo, EGY", status="pending", is_fraud=True,
        fraud_notes=(
            "Fraud ring: shares device, IP, and recipient with CUST-013 (Ahmed "
            "Hassan). ZERO trades — pure deposit-and-withdraw. 1-week account, "
            "withdrawing 99% of deposit to third-party. "
            "Withdrawal within 10 min of Ahmed's (coordinated timing)."
        ),
        requested_at=_ago(days=3, minutes=2), created_at=_ago(days=3, minutes=2),
    ))


async def _seed_carlos(s: AsyncSession) -> None:
    """Carlos Mendez — The Velocity Abuser."""
    cid, pm = _id("carlos"), _id("carlos.pm.visa")
    dev1, dev2, dev3 = _id("carlos.device.1"), _id("carlos.device.2"), _id("carlos.device.3")
    fp1 = "e1e2e3e4f5f6e1e2e3e4f5f6e1e2e3e4"
    fp2 = "e2e3e4e5f6f7e2e3e4e5f6f7e2e3e4e5"
    fp3 = "e3e4e5e6f7f8e3e4e5e6f7f8e3e4e5e6"
    vpn_ip = "185.199.108.55"

    s.add(Customer(
        id=cid, external_id="CUST-015", name="Carlos Mendez",
        email="carlos.mendez@example.com", country="MEX",
        registration_date=_ago(days=90), created_at=_ago(days=90), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="6677", is_verified=True, added_at=_ago(days=85),
        last_used_at=_ago(days=10), created_at=_ago(days=85),
    ))
    for d_id, fp, os_val in [
        (dev1, fp1, "Windows 10"), (dev2, fp2, "Android 13"), (dev3, fp3, "Linux"),
    ]:
        s.add(Device(
            id=d_id, customer_id=cid, fingerprint=fp, os=os_val,
            browser="Chrome 121", screen_resolution="1920x1080",
            first_seen_at=_ago(days=30), last_seen_at=_ago(hours=1),
            is_trusted=False, created_at=_ago(days=30),
        ))
    s.add(IPHistory(
        customer_id=cid, ip_address="187.190.100.20", location="Mexico City, MEX",
        first_seen_at=_ago(days=85), last_seen_at=_ago(days=5), created_at=_ago(days=85),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=vpn_ip, location="VPN Exit, USA", is_vpn=True,
        first_seen_at=_ago(hours=2), last_seen_at=_ago(minutes=10), created_at=_ago(hours=2),
    ))
    s.add_all(_gen_deposits(cid, pm, 5, _ago(days=30), _ago(days=5), 500, 2000, "187.190.100.20"))
    s.add_all(_gen_trades(cid, 20, _ago(days=30), _ago(days=5), 50, 500))
    for i in range(5):
        s.add(Withdrawal(
            id=_id(f"carlos.wd.{i}"), customer_id=cid, amount=Decimal("400.00"),
            currency="USD", payment_method_id=pm, recipient_name="Carlos Mendez",
            recipient_account="MX012345678901234567890123456", ip_address=vpn_ip,
            device_fingerprint=[fp1, fp2, fp3, fp1, fp2][i],
            location="VPN Exit, USA", status="pending", is_fraud=True,
            fraud_notes=(
                "Velocity abuse: 5 withdrawals in 1 hour ($400 each = $2000), "
                "3 different devices, VPN IP. Structuring pattern to stay under "
                "reporting thresholds."
            ),
            requested_at=_ago(days=12) - timedelta(minutes=50 - i * 10),
            created_at=_ago(days=12) - timedelta(minutes=50 - i * 10),
        ))


async def _seed_nina(s: AsyncSession) -> None:
    """Nina Volkov — The Geo Impossible + Rapid Funding Cycle.

    1-month account, UKR. IP history shows Kyiv, then 30 minutes later
    São Paulo (impossible travel). New device appears in São Paulo.
    Also exhibits rapid_funding_cycle: 3 deposit→withdrawal cycles
    within 6 hours each over the past 3 days.
    Triggers: geographic impossibility, new device, rapid_funding_cycle.
    """
    cid, pm = _id("nina"), _id("nina.pm.visa")
    dev_orig, dev_new = _id("nina.device.orig"), _id("nina.device.new")
    fp_orig = "f1f2f3f4a5a6f1f2f3f4a5a6f1f2f3f4"
    fp_new = "aabb11cc22dd33ee44ff55aa66bb77cc"
    ip_kyiv, ip_saopaulo = "91.237.100.15", "177.71.88.99"

    s.add(Customer(
        id=cid, external_id="CUST-016", name="Nina Volkov",
        email="nina.volkov@example.com", country="UKR",
        registration_date=_ago(days=30), created_at=_ago(days=30), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="6677", is_verified=True, added_at=_ago(days=28),
        last_used_at=_ago(days=5), created_at=_ago(days=28),
    ))
    s.add(Device(
        id=dev_orig, customer_id=cid, fingerprint=fp_orig, os="Windows 11",
        browser="Chrome 121", screen_resolution="1920x1080",
        first_seen_at=_ago(days=28), last_seen_at=_ago(minutes=35),
        is_trusted=True, created_at=_ago(days=28),
    ))
    s.add(Device(
        id=dev_new, customer_id=cid, fingerprint=fp_new, os="macOS 14",
        browser="Safari 17", screen_resolution="2560x1440",
        first_seen_at=_ago(minutes=5), last_seen_at=_ago(minutes=1),
        is_trusted=False, created_at=_ago(minutes=5),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip_kyiv, location="Kyiv, UKR",
        first_seen_at=_ago(days=28), last_seen_at=_ago(minutes=35), created_at=_ago(days=28),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip_saopaulo, location="São Paulo, BRA",
        first_seen_at=_ago(minutes=5), last_seen_at=_ago(minutes=1), created_at=_ago(minutes=5),
    ))
    s.add_all(_gen_deposits(cid, pm, 3, _ago(days=25), _ago(days=5), 500, 1500, ip_kyiv))
    s.add_all(_gen_trades(cid, 8, _ago(days=25), _ago(days=3), 50, 500))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 2, _ago(days=20), _ago(days=8),
        200, 500, ip_kyiv, fp_orig, "Nina Volkov", "UA213223130000026007233566001",
        "Kyiv, UKR",
    ))

    # ── Rapid funding cycles (rapid_funding_cycle pattern) ──
    # 3 deposit→withdrawal cycles, each within ~4 hours, spread over 3 days
    for cycle_i, cycle_start_days in enumerate([3, 2, 1]):
        # Deposit at cycle start
        dep_ts = _ago(days=cycle_start_days, hours=5)
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("800.00"), currency="USD", status="success",
            payment_method_id=pm, ip_address=ip_kyiv,
            timestamp=dep_ts, created_at=dep_ts,
        ))
        # Withdrawal ~3-4 hours later (within 6 hour window)
        wd_ts = dep_ts + timedelta(hours=3, minutes=30 + cycle_i * 10)
        s.add(Withdrawal(
            id=_id(f"nina.wd.cycle.{cycle_i}"), customer_id=cid,
            amount=Decimal("750.00"), currency="USD", payment_method_id=pm,
            recipient_name="Nina Volkov",
            recipient_account="UA213223130000026007233566001",
            ip_address=ip_kyiv, device_fingerprint=fp_orig,
            location="Kyiv, UKR", status="approved",
            is_fraud=True,
            fraud_notes=(
                f"Rapid funding cycle {cycle_i + 1}/3: deposit $800 then withdraw "
                f"$750 within ~4 hours. Pattern repeated 3 times in 3 days."
            ),
            requested_at=wd_ts, processed_at=wd_ts + timedelta(seconds=5),
            created_at=wd_ts,
        ))

    # Withdrawal from São Paulo IP with new device — impossible travel!
    s.add(Withdrawal(
        id=_id("nina.wd.pending"), customer_id=cid, amount=Decimal("2000.00"),
        currency="USD", payment_method_id=pm, recipient_name="Nina Volkov",
        recipient_account="UA213223130000026007233566001",
        ip_address=ip_saopaulo, device_fingerprint=fp_new,
        location="São Paulo, BRA", status="pending", is_fraud=True,
        fraud_notes=(
            "Impossible travel: Kyiv IP 35 min ago, now São Paulo. New device "
            "appeared at São Paulo location. Amount ($2000) is 4x her normal "
            "withdrawal range. Also exhibits rapid_funding_cycle: 3 deposit→withdraw "
            "cycles in 3 days (each within ~4 hours). Likely account takeover."
        ),
        requested_at=_ago(days=8), created_at=_ago(days=8),
    ))
