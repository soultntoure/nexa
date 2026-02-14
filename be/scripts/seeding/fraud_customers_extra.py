"""Extra fraud customer seeders (6) — CUST-017 to CUST-022."""

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import (
    Customer, Device, IPHistory, PaymentMethod, Trade, Transaction, Withdrawal,
)

from .constants import FP_ATO_STOLEN, NOW, _ago, _id
from .generators import _gen_deposits


async def _seed_liam(s: AsyncSession) -> None:
    """Liam Chen — Refund Abuser.

    3 chargebacks in 30 days after profitable trades.
    Disputes legitimate withdrawals, uses different cards.
    """
    cid = _id("liam")
    pm1, pm2, pm3 = _id("liam.pm.1"), _id("liam.pm.2"), _id("liam.pm.3")
    dev = _id("liam.device")
    ip = "103.44.21.88"

    s.add(Customer(
        id=cid, external_id="CUST-017", name="Liam Chen",
        email="liam.chen@example.com", country="SGP",
        registration_date=_ago(days=60), created_at=_ago(days=60), updated_at=NOW,
    ))
    for i, (pm_id, last4, prov) in enumerate([
        (pm1, "3301", "visa"), (pm2, "3302", "mastercard"), (pm3, "3303", "visa"),
    ]):
        s.add(PaymentMethod(
            id=pm_id, customer_id=cid, type="card", provider=prov,
            last_four=last4, is_verified=True,
            added_at=_ago(days=55 - i * 10), last_used_at=_ago(days=5 - i),
            created_at=_ago(days=55 - i * 10),
        ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint="bb11aa22cc33dd44ee55ff6677889900",
        os="macOS 14", browser="Safari 17", screen_resolution="2560x1440",
        first_seen_at=_ago(days=60), last_seen_at=_ago(hours=2),
        is_trusted=True, created_at=_ago(days=60),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Singapore, SGP",
        first_seen_at=_ago(days=60), last_seen_at=_ago(hours=2),
        created_at=_ago(days=60),
    ))
    # Profitable trades
    for i in range(6):
        opened = _ago(days=45 - i * 5)
        s.add(Trade(
            id=uuid.uuid4(), customer_id=cid, instrument="BTC/USD",
            trade_type="buy", amount=Decimal("500.00"), pnl=Decimal("120.00"),
            opened_at=opened, closed_at=opened + timedelta(hours=3),
            created_at=opened,
        ))
    # Deposits on different cards
    for pm_id in [pm1, pm2, pm3]:
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("2000.00"), currency="USD", status="success",
            payment_method_id=pm_id, ip_address=ip,
            timestamp=_ago(days=50), created_at=_ago(days=50),
        ))
    # 3 chargebacks (failed refunds after withdrawals)
    for i, pm_id in enumerate([pm1, pm2, pm3]):
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("2000.00"), currency="USD", status="failed",
            payment_method_id=pm_id, error_code="chargeback",
            ip_address=ip,
            timestamp=_ago(days=25 - i * 8), created_at=_ago(days=25 - i * 8),
        ))
    s.add(Withdrawal(
        id=_id("liam.wd.pending"), customer_id=cid, amount=Decimal("3500.00"),
        currency="USD", payment_method_id=pm3, recipient_name="Liam Chen",
        recipient_account="SG1234567890123456", ip_address=ip,
        device_fingerprint="bb11aa22cc33dd44ee55ff6677889900",
        location="Singapore, SGP", status="pending", is_fraud=True,
        fraud_notes=(
            "Refund abuse: 3 chargebacks in 30 days across 3 different cards. "
            "Disputes after profitable BTC trades. Attempting $3500 withdrawal."
        ),
        requested_at=NOW, created_at=NOW,
    ))


async def _seed_olga(s: AsyncSession) -> None:
    """Olga Ivanova — Smurfing / Structuring.

    12 deposits of $990 each (under $1000 threshold), then single $11k withdrawal.
    Account only 2 days old.
    """
    cid, pm, dev = _id("olga"), _id("olga.pm.visa"), _id("olga.device")
    ip = "178.35.22.100"

    s.add(Customer(
        id=cid, external_id="CUST-018", name="Olga Ivanova",
        email="olga.ivanova@example.com", country="RUS",
        registration_date=_ago(days=2), created_at=_ago(days=2), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="7788", is_verified=True,
        added_at=_ago(days=2), last_used_at=_ago(hours=3), created_at=_ago(days=2),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint="dd44ee55ff66aa77bb88cc99dd00ee11",
        os="Windows 11", browser="Chrome 122", screen_resolution="1920x1080",
        first_seen_at=_ago(days=2), last_seen_at=_ago(hours=3),
        is_trusted=False, created_at=_ago(days=2),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Moscow, RUS",
        first_seen_at=_ago(days=2), last_seen_at=_ago(hours=3),
        created_at=_ago(days=2),
    ))
    # 12 deposits of $990 each — just under $1000 threshold
    for i in range(12):
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("990.00"), currency="USD", status="success",
            payment_method_id=pm, ip_address=ip,
            timestamp=_ago(hours=36 - i * 2), created_at=_ago(hours=36 - i * 2),
        ))
    s.add(Withdrawal(
        id=_id("olga.wd.pending"), customer_id=cid, amount=Decimal("11000.00"),
        currency="USD", payment_method_id=pm, recipient_name="Olga Ivanova",
        recipient_account="RU0198765432109876543210987", ip_address=ip,
        device_fingerprint="dd44ee55ff66aa77bb88cc99dd00ee11",
        location="Moscow, RUS", status="pending", is_fraud=True,
        fraud_notes=(
            "Structuring/smurfing: 12 deposits of $990 each (just under $1000 "
            "reporting threshold) over 36 hours. Single $11k withdrawal. "
            "Account only 2 days old. Zero trades."
        ),
        requested_at=NOW, created_at=NOW,
    ))


async def _seed_dmitri(s: AsyncSession) -> None:
    """Dmitri Kozlov — Account Takeover (Credential Stuffing).

    6-month dormant account. Sudden new device + new IP + new country.
    Password reset, then immediate $8k withdrawal.
    Shares device with Elena (CUST-022).
    """
    cid, pm = _id("dmitri"), _id("dmitri.pm.visa")
    dev_old, dev_new = _id("dmitri.device.old"), _id("dmitri.device.new")
    ip_old, ip_new = "89.123.45.67", "203.0.113.42"

    s.add(Customer(
        id=cid, external_id="CUST-019", name="Dmitri Kozlov",
        email="dmitri.kozlov@example.com", country="RUS",
        registration_date=_ago(days=365), created_at=_ago(days=365), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="5566", is_verified=True,
        added_at=_ago(days=360), last_used_at=_ago(days=180),
        created_at=_ago(days=360),
    ))
    s.add(Device(
        id=dev_old, customer_id=cid, fingerprint="aa11bb22cc33dd44ee55ff6677881122",
        os="Windows 10", browser="Firefox 118", screen_resolution="1366x768",
        first_seen_at=_ago(days=365), last_seen_at=_ago(days=180),
        is_trusted=True, created_at=_ago(days=365),
    ))
    s.add(Device(
        id=dev_new, customer_id=cid, fingerprint=FP_ATO_STOLEN,
        os="macOS 14", browser="Chrome 122", screen_resolution="2560x1440",
        first_seen_at=_ago(minutes=30), last_seen_at=_ago(minutes=5),
        is_trusted=False, created_at=_ago(minutes=30),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip_old, location="Saint Petersburg, RUS",
        first_seen_at=_ago(days=365), last_seen_at=_ago(days=180),
        created_at=_ago(days=365),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip_new, location="Lagos, NGA",
        first_seen_at=_ago(minutes=30), last_seen_at=_ago(minutes=5),
        created_at=_ago(minutes=30),
    ))
    # Historical trading (before dormancy)
    s.add_all(_gen_deposits(cid, pm, 5, _ago(days=350), _ago(days=200), 500, 2000, ip_old))
    for i in range(10):
        opened = _ago(days=340 - i * 15)
        s.add(Trade(
            id=uuid.uuid4(), customer_id=cid, instrument="EUR/USD",
            trade_type="buy", amount=Decimal("300.00"), pnl=Decimal("45.00"),
            opened_at=opened, closed_at=opened + timedelta(hours=6),
            created_at=opened,
        ))
    s.add(Withdrawal(
        id=_id("dmitri.wd.pending"), customer_id=cid, amount=Decimal("8000.00"),
        currency="USD", payment_method_id=pm, recipient_name="Dmitri Kozlov",
        recipient_account="RU0111222333444555666777888", ip_address=ip_new,
        device_fingerprint=FP_ATO_STOLEN, location="Lagos, NGA",
        status="pending", is_fraud=True,
        fraud_notes=(
            "ATO via credential stuffing: 6-month dormant account. New device "
            "(shared with CUST-022 Elena), new IP (Lagos, NGA vs historical "
            "Saint Petersburg, RUS). $8k withdrawal — entire balance."
        ),
        requested_at=NOW, created_at=NOW,
    ))
