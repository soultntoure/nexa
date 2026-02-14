"""Escalate customer seeders (4) — expected outcome: ESCALATE."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import (
    Customer, Device, IPHistory, PaymentMethod, Withdrawal,
)

from .constants import NOW, _ago, _id
from .generators import _gen_deposits, _gen_past_withdrawals, _gen_trades


async def _seed_david(s: AsyncSession) -> None:
    """David Park — The Business Traveler."""
    cid, pm, dev = _id("david"), _id("david.pm.visa"), _id("david.device")
    fp = "a1a2a3a4b5b6a1a2a3a4b5b6a1a2a3a4"
    ip_home = "175.212.50.60"

    s.add(Customer(
        id=cid, external_id="CUST-007", name="David Park",
        email="david.park@example.com", country="KOR",
        registration_date=_ago(days=180), created_at=_ago(days=180), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="9012", is_verified=True, added_at=_ago(days=175),
        last_used_at=_ago(days=5), created_at=_ago(days=175),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="macOS 14",
        browser="Chrome 121", screen_resolution="2560x1600",
        first_seen_at=_ago(days=180), last_seen_at=_ago(hours=1),
        is_trusted=True, created_at=_ago(days=180),
    ))
    ip_entries = [
        (_ago(days=90), ip_home, "Seoul, KOR", False),
        (_ago(days=25), "103.5.140.99", "Tokyo, JPN", False),
        (_ago(days=12), "72.229.55.77", "New York, USA", False),
        (_ago(days=5), ip_home, "Seoul, KOR", False),
        (_ago(hours=3), "185.199.110.20", "VPN Exit, NLD", True),
    ]
    for dt, ip, loc, vpn in ip_entries:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location=loc, is_vpn=vpn,
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 10, _ago(days=30), _ago(days=1), 500, 2000, ip_home))
    s.add_all(_gen_trades(cid, 50, _ago(days=30), _ago(days=1), 100, 1500))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 4, _ago(days=28), _ago(days=3),
        300, 1200, ip_home, fp, "David Park", "KR1234567890123456789012", "Seoul, KOR",
    ))
    s.add(Withdrawal(
        id=_id("david.wd.pending"), customer_id=cid, amount=Decimal("1000.00"),
        currency="USD", payment_method_id=pm, recipient_name="David Park",
        recipient_account="KR1234567890123456789012",
        ip_address="185.199.110.20", device_fingerprint=fp,
        location="VPN Exit, NLD", status="pending",
        requested_at=_ago(days=4), created_at=_ago(days=4),
    ))


async def _seed_maria(s: AsyncSession) -> None:
    """Maria Santos — The New High-Roller."""
    cid, pm, dev = _id("maria"), _id("maria.pm.bank"), _id("maria.device")
    fp, ip = "b1b2b3b4c5c6b1b2b3b4c5c6b1b2b3b4", "177.71.200.30"

    s.add(Customer(
        id=cid, external_id="CUST-008", name="Maria Santos",
        email="maria.santos@example.com", country="BRA",
        registration_date=_ago(days=21), created_at=_ago(days=21), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="bank_transfer", provider="itau",
        is_verified=True, added_at=_ago(days=2), last_used_at=None, created_at=_ago(days=2),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="Android 14",
        browser="Chrome Mobile 121", screen_resolution="1080x2400",
        first_seen_at=_ago(days=21), last_seen_at=_ago(hours=1),
        is_trusted=False, created_at=_ago(days=21),
    ))
    for dt in [_ago(days=21), _ago(days=10), _ago(hours=2)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="São Paulo, BRA",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 3, _ago(days=21), _ago(days=3), 3000, 8000, ip))
    s.add_all(_gen_trades(cid, 15, _ago(days=21), _ago(days=1), 500, 3000))
    s.add(Withdrawal(
        id=_id("maria.wd.pending"), customer_id=cid, amount=Decimal("5000.00"),
        currency="USD", payment_method_id=pm, recipient_name="Maria Santos",
        recipient_account="BR1500000000000010932840814P2",
        ip_address=ip, device_fingerprint=fp, location="São Paulo, BRA",
        status="pending", requested_at=_ago(days=11), created_at=_ago(days=11),
    ))


async def _seed_tom(s: AsyncSession) -> None:
    """Tom Brown — The Method Switcher."""
    cid = _id("tom")
    pm_old, pm_new = _id("tom.pm.visa"), _id("tom.pm.btc")
    dev = _id("tom.device")
    fp, ip = "c1c2c3c4d5d6c1c2c3c4d5d6c1c2c3c4", "203.206.50.10"

    s.add(Customer(
        id=cid, external_id="CUST-009", name="Tom Brown",
        email="tom.brown@example.com", country="AUS",
        registration_date=_ago(days=365), created_at=_ago(days=365), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm_old, customer_id=cid, type="card", provider="visa",
        last_four="3344", is_verified=True, added_at=_ago(days=360),
        last_used_at=_ago(days=7), created_at=_ago(days=360),
    ))
    s.add(PaymentMethod(
        id=pm_new, customer_id=cid, type="crypto", provider="btc",
        is_verified=True, added_at=_ago(days=1), last_used_at=None, created_at=_ago(days=1),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="Windows 11",
        browser="Chrome 121", screen_resolution="1920x1080",
        first_seen_at=_ago(days=350), last_seen_at=_ago(hours=3),
        is_trusted=True, created_at=_ago(days=350),
    ))
    for dt in [_ago(days=300), _ago(days=90), _ago(days=5)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="Sydney, AUS",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm_old, 12, _ago(days=30), _ago(days=2), 300, 1500, ip, "AUD"))
    s.add_all(_gen_trades(cid, 45, _ago(days=30), _ago(days=2), 100, 1000))
    s.add_all(_gen_past_withdrawals(
        cid, pm_old, 6, _ago(days=28), _ago(days=3),
        200, 1000, ip, fp, "Tom Brown", "AU123456789012345678", "Sydney, AUS", "AUD",
    ))
    s.add(Withdrawal(
        id=_id("tom.wd.pending"), customer_id=cid, amount=Decimal("800.00"),
        currency="AUD", payment_method_id=pm_new, recipient_name="Tom Brown",
        recipient_account="bc1q42lja79elem0anu8q860g3ez26r0ckpv6e0gah",
        ip_address=ip, device_fingerprint=fp, location="Sydney, AUS",
        status="pending", requested_at=_ago(days=17), created_at=_ago(days=17),
    ))


async def _seed_yuki(s: AsyncSession) -> None:
    """Yuki Tanaka — The Dormant Returner."""
    cid, pm = _id("yuki"), _id("yuki.pm.visa")
    dev_old, dev_new = _id("yuki.device.old"), _id("yuki.device.new")
    fp_old = "d1d2d3d4e5e6d1d2d3d4e5e6d1d2d3d4"
    fp_new = "ff11ff22ff33ff44ff55ff66ff77ff88"
    ip = "103.5.140.70"

    s.add(Customer(
        id=cid, external_id="CUST-010", name="Yuki Tanaka",
        email="yuki.tanaka@example.com", country="JPN",
        registration_date=_ago(days=730), created_at=_ago(days=730), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="5566", is_verified=True, added_at=_ago(days=720),
        last_used_at=_ago(days=5), created_at=_ago(days=720),
    ))
    s.add(Device(
        id=dev_old, customer_id=cid, fingerprint=fp_old, os="Windows 10",
        browser="Chrome 110", screen_resolution="1920x1080",
        first_seen_at=_ago(days=720), last_seen_at=_ago(days=180),
        is_trusted=True, created_at=_ago(days=720),
    ))
    s.add(Device(
        id=dev_new, customer_id=cid, fingerprint=fp_new, os="Windows 11",
        browser="Chrome 122", screen_resolution="2560x1440",
        first_seen_at=_ago(days=5), last_seen_at=_ago(hours=2),
        is_trusted=False, created_at=_ago(days=5),
    ))
    for dt, ip_addr, loc in [
        (_ago(days=600), ip, "Osaka, JPN"),
        (_ago(days=200), ip, "Osaka, JPN"),
        (_ago(days=5), ip, "Osaka, JPN"),
    ]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip_addr, location=loc,
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 8, _ago(days=30), _ago(days=6), 400, 1500, ip))
    s.add_all(_gen_trades(cid, 40, _ago(days=30), _ago(days=6), 100, 800))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 4, _ago(days=28), _ago(days=7),
        200, 800, ip, fp_old, "Yuki Tanaka", "JP1234567890123456", "Osaka, JPN",
    ))
    s.add_all(_gen_trades(cid, 3, _ago(days=4), _ago(days=1), 100, 500))
    s.add(Withdrawal(
        id=_id("yuki.wd.pending"), customer_id=cid, amount=Decimal("1500.00"),
        currency="USD", payment_method_id=pm, recipient_name="Yuki Tanaka",
        recipient_account="JP1234567890123456", ip_address=ip,
        device_fingerprint=fp_new, location="Osaka, JPN", status="pending",
        requested_at=_ago(days=23), created_at=_ago(days=23),
    ))
