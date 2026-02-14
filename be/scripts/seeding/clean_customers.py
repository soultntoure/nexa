"""Clean customer seeders (6) — expected outcome: APPROVE."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import (
    Customer, Device, IPHistory, PaymentMethod, Withdrawal,
)

from .constants import NOW, _ago, _id
from .generators import _gen_deposits, _gen_past_withdrawals, _gen_trades


async def _seed_sarah(s: AsyncSession) -> None:
    """Sarah Chen — The Reliable Regular."""
    cid, pm, dev = _id("sarah"), _id("sarah.pm.visa"), _id("sarah.device")
    fp, ip = "f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4", "51.148.20.30"

    s.add(Customer(
        id=cid, external_id="CUST-001", name="Sarah Chen",
        email="sarah.chen@example.com", country="GBR",
        registration_date=_ago(days=540), created_at=_ago(days=540), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="4532", is_verified=True, added_at=_ago(days=530),
        last_used_at=_ago(days=2), created_at=_ago(days=530),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="Windows 11",
        browser="Chrome 121", screen_resolution="1920x1080",
        first_seen_at=_ago(days=365), last_seen_at=_ago(hours=2),
        is_trusted=True, created_at=_ago(days=365),
    ))
    for dt, loc in [
        (_ago(days=400), "London, GBR"), (_ago(days=200), "London, GBR"),
        (_ago(days=30), "London, GBR"), (_ago(days=1), "London, GBR"),
    ]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location=loc,
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 15, _ago(days=30), _ago(days=1), 500, 2000, ip))
    s.add_all(_gen_trades(cid, 80, _ago(days=30), _ago(days=1), 100, 1500))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 8, _ago(days=28), _ago(days=2),
        200, 800, ip, fp, "Sarah Chen", "GB29NWBK60161331926819", "London, GBR",
    ))
    s.add(Withdrawal(
        id=_id("sarah.wd.pending"), customer_id=cid, amount=Decimal("500.00"),
        currency="USD", payment_method_id=pm, recipient_name="Sarah Chen",
        recipient_account="GB29NWBK60161331926819", ip_address=ip,
        device_fingerprint=fp, location="London, GBR", status="pending",
        is_fraud=False,
        fraud_notes="Routine self-withdrawal from consistent IP/device/location",
        requested_at=_ago(days=2), created_at=_ago(days=2),
    ))


async def _seed_james(s: AsyncSession) -> None:
    """James Wilson — The VIP Whale."""
    cid, pm, dev = _id("james"), _id("james.pm.bank"), _id("james.device")
    fp, ip = "b2c3d4e5f6a7b2c3d4e5f6a7b2c3d4e5", "72.229.30.40"

    s.add(Customer(
        id=cid, external_id="CUST-002", name="James Wilson",
        email="james.wilson@example.com", country="USA",
        registration_date=_ago(days=1095), created_at=_ago(days=1095), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="bank_transfer", provider="chase",
        is_verified=True, added_at=_ago(days=1090),
        last_used_at=_ago(days=3), created_at=_ago(days=1090),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="macOS 14",
        browser="Safari 17", screen_resolution="2560x1440",
        first_seen_at=_ago(days=900), last_seen_at=_ago(hours=5),
        is_trusted=True, created_at=_ago(days=900),
    ))
    for dt in [_ago(days=800), _ago(days=300), _ago(days=30), _ago(days=1)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="New York, USA",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 20, _ago(days=30), _ago(days=1), 5000, 25000, ip))
    s.add_all(_gen_trades(cid, 150, _ago(days=30), _ago(days=1), 500, 8000))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 12, _ago(days=28), _ago(days=2),
        5000, 18000, ip, fp, "James Wilson", "021000021-987654321", "New York, USA",
    ))
    s.add(Withdrawal(
        id=_id("james.wd.pending"), customer_id=cid, amount=Decimal("15000.00"),
        currency="USD", payment_method_id=pm, recipient_name="James Wilson",
        recipient_account="021000021-987654321", ip_address=ip,
        device_fingerprint=fp, location="New York, USA", status="pending",
        is_fraud=False,
        fraud_notes="VIP whale, $15k within normal range for 3-year active trader",
        requested_at=_ago(days=6), created_at=_ago(days=6),
    ))


async def _seed_aisha(s: AsyncSession) -> None:
    """Aisha Mohammed — The E-Wallet Loyalist."""
    cid, pm, dev = _id("aisha"), _id("aisha.pm.skrill"), _id("aisha.device")
    fp, ip = "c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6", "94.56.78.90"

    s.add(Customer(
        id=cid, external_id="CUST-003", name="Aisha Mohammed",
        email="aisha.mo@example.com", country="ARE",
        registration_date=_ago(days=240), created_at=_ago(days=240), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="ewallet", provider="skrill",
        is_verified=True, added_at=_ago(days=235),
        last_used_at=_ago(days=5), created_at=_ago(days=235),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="iOS 17",
        browser="Safari Mobile", screen_resolution="1170x2532",
        first_seen_at=_ago(days=240), last_seen_at=_ago(hours=8),
        is_trusted=True, created_at=_ago(days=240),
    ))
    for dt in [_ago(days=200), _ago(days=60), _ago(days=7)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="Dubai, ARE",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 8, _ago(days=30), _ago(days=2), 200, 800, ip))
    s.add_all(_gen_trades(cid, 40, _ago(days=30), _ago(days=2), 50, 500))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 5, _ago(days=28), _ago(days=3),
        100, 400, ip, fp, "Aisha Mohammed", "AE070331234567890123456", "Dubai, ARE",
    ))
    s.add(Withdrawal(
        id=_id("aisha.wd.pending"), customer_id=cid, amount=Decimal("200.00"),
        currency="USD", payment_method_id=pm, recipient_name="Aisha Mohammed",
        recipient_account="AE070331234567890123456", ip_address=ip,
        device_fingerprint=fp, location="Dubai, ARE", status="pending",
        is_fraud=False,
        fraud_notes="Small routine withdrawal, consistent profile and device",
        requested_at=_ago(days=10), created_at=_ago(days=10),
    ))


async def _seed_kenji(s: AsyncSession) -> None:
    """Kenji Sato — The Crypto Consistent."""
    cid, pm, dev = _id("kenji"), _id("kenji.pm.btc"), _id("kenji.device")
    fp, ip = "d4e5f6a7b8c9d4e5f6a7b8c9d4e5f6a7", "103.5.140.50"

    s.add(Customer(
        id=cid, external_id="CUST-004", name="Kenji Sato",
        email="kenji.sato@example.com", country="JPN",
        registration_date=_ago(days=365), created_at=_ago(days=365), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="crypto", provider="btc",
        is_verified=True, added_at=_ago(days=360),
        last_used_at=_ago(days=3), created_at=_ago(days=360),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="Windows 11",
        browser="Firefox 122", screen_resolution="2560x1440",
        first_seen_at=_ago(days=365), last_seen_at=_ago(hours=4),
        is_trusted=True, created_at=_ago(days=365),
    ))
    for dt in [_ago(days=300), _ago(days=100), _ago(days=5)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="Tokyo, JPN",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 12, _ago(days=30), _ago(days=1), 500, 3000, ip))
    s.add_all(_gen_trades(cid, 60, _ago(days=30), _ago(days=1), 200, 2000))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 6, _ago(days=28), _ago(days=2),
        400, 1500, ip, fp, "Kenji Sato",
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "Tokyo, JPN",
    ))
    s.add(Withdrawal(
        id=_id("kenji.wd.pending"), customer_id=cid, amount=Decimal("1200.00"),
        currency="USD", payment_method_id=pm, recipient_name="Kenji Sato",
        recipient_account="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        ip_address=ip, device_fingerprint=fp, location="Tokyo, JPN",
        status="pending", is_fraud=False,
        fraud_notes="Crypto-native user, consistent BTC wallet used 6 prior times",
        requested_at=_ago(days=14), created_at=_ago(days=14),
    ))


async def _seed_emma(s: AsyncSession) -> None:
    """Emma Davies — The Low-Volume Veteran."""
    cid, pm, dev = _id("emma"), _id("emma.pm.visa"), _id("emma.device")
    fp, ip = "e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8", "51.148.88.12"

    s.add(Customer(
        id=cid, external_id="CUST-005", name="Emma Davies",
        email="emma.davies@example.com", country="GBR",
        registration_date=_ago(days=730), created_at=_ago(days=730), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="mastercard",
        last_four="8821", is_verified=True, added_at=_ago(days=725),
        last_used_at=_ago(days=10), created_at=_ago(days=725),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="macOS 13",
        browser="Chrome 120", screen_resolution="1440x900",
        first_seen_at=_ago(days=700), last_seen_at=_ago(days=2),
        is_trusted=True, created_at=_ago(days=700),
    ))
    for dt in [_ago(days=600), _ago(days=180), _ago(days=10)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="Manchester, GBR",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 6, _ago(days=30), _ago(days=3), 100, 500, ip, "GBP"))
    s.add_all(_gen_trades(cid, 25, _ago(days=30), _ago(days=3), 20, 200))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 4, _ago(days=28), _ago(days=5),
        50, 250, ip, fp, "Emma Davies", "GB82WEST12345698765432",
        "Manchester, GBR", "GBP",
    ))
    s.add(Withdrawal(
        id=_id("emma.wd.pending"), customer_id=cid, amount=Decimal("150.00"),
        currency="GBP", payment_method_id=pm, recipient_name="Emma Davies",
        recipient_account="GB82WEST12345698765432", ip_address=ip,
        device_fingerprint=fp, location="Manchester, GBR", status="pending",
        is_fraud=False,
        fraud_notes="Low-volume veteran, small withdrawal matches 2-year pattern",
        requested_at=_ago(days=20), created_at=_ago(days=20),
    ))


async def _seed_raj(s: AsyncSession) -> None:
    """Raj Patel — The Premium Trader."""
    cid, pm, dev = _id("raj"), _id("raj.pm.bank"), _id("raj.device")
    fp, ip = "f6a7b8c9d0e1f6a7b8c9d0e1f6a7b8c9", "49.36.120.80"

    s.add(Customer(
        id=cid, external_id="CUST-006", name="Raj Patel",
        email="raj.patel@example.com", country="IND",
        registration_date=_ago(days=365), created_at=_ago(days=365), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="bank_transfer", provider="hdfc",
        is_verified=True, added_at=_ago(days=360),
        last_used_at=_ago(days=2), created_at=_ago(days=360),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=fp, os="Windows 11",
        browser="Edge 121", screen_resolution="1920x1080",
        first_seen_at=_ago(days=360), last_seen_at=_ago(hours=6),
        is_trusted=True, created_at=_ago(days=360),
    ))
    for dt in [_ago(days=300), _ago(days=90), _ago(days=3)]:
        s.add(IPHistory(
            customer_id=cid, ip_address=ip, location="Mumbai, IND",
            first_seen_at=dt, last_seen_at=dt, created_at=dt,
        ))
    s.add_all(_gen_deposits(cid, pm, 18, _ago(days=30), _ago(days=1), 1000, 5000, ip))
    s.add_all(_gen_trades(cid, 120, _ago(days=30), _ago(days=1), 200, 3000))
    s.add_all(_gen_past_withdrawals(
        cid, pm, 10, _ago(days=28), _ago(days=2),
        800, 4000, ip, fp, "Raj Patel", "HDFC0001234-9876543210", "Mumbai, IND",
    ))
    s.add(Withdrawal(
        id=_id("raj.wd.pending"), customer_id=cid, amount=Decimal("3000.00"),
        currency="USD", payment_method_id=pm, recipient_name="Raj Patel",
        recipient_account="HDFC0001234-9876543210", ip_address=ip,
        device_fingerprint=fp, location="Mumbai, IND", status="pending",
        is_fraud=False,
        fraud_notes="Active premium trader, $3k within normal range of 120+ trades",
        requested_at=_ago(days=25), created_at=_ago(days=25),
    ))
