"""Extra fraud customer seeders (continued) — CUST-020 to CUST-022."""

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import (
    Customer, Device, IPHistory, PaymentMethod, Trade, Transaction, Withdrawal,
)

from .constants import (
    FP_ATO_STOLEN, FP_FRAUD_RING, IP_FRAUD_RING, IP_MULE_RING,
    NOW, _ago, _id,
)


async def _seed_priya(s: AsyncSession) -> None:
    """Priya Sharma — Mule Account.

    Receives funds from Ahmed/Fatima fraud ring accounts.
    Zero trades, quick pass-through deposits to withdrawals.
    Shared IP with ring, same recipient as ring.
    """
    cid, pm, dev = _id("priya"), _id("priya.pm.visa"), _id("priya.device")

    s.add(Customer(
        id=cid, external_id="CUST-020", name="Priya Sharma",
        email="priya.sharma@example.com", country="IND",
        registration_date=_ago(days=3), created_at=_ago(days=3), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="9911", is_verified=True,
        added_at=_ago(days=3), last_used_at=_ago(hours=4), created_at=_ago(days=3),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=FP_FRAUD_RING,
        os="Android 14", browser="Chrome Mobile 122", screen_resolution="1080x2400",
        first_seen_at=_ago(days=3), last_seen_at=_ago(hours=1),
        is_trusted=False, created_at=_ago(days=3),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=IP_MULE_RING, location="Mumbai, IND",
        first_seen_at=_ago(days=3), last_seen_at=_ago(hours=1),
        created_at=_ago(days=3),
    ))
    # Pass-through deposits (2 deposits, quick withdrawal)
    for i in range(2):
        s.add(Transaction(
            id=uuid.uuid4(), customer_id=cid, type="deposit",
            amount=Decimal("2500.00"), currency="USD", status="success",
            payment_method_id=pm, ip_address=IP_MULE_RING,
            timestamp=_ago(days=2, hours=i * 6),
            created_at=_ago(days=2, hours=i * 6),
        ))
    # Zero trades — pure pass-through
    s.add(Withdrawal(
        id=_id("priya.wd.pending"), customer_id=cid, amount=Decimal("4800.00"),
        currency="USD", payment_method_id=pm,
        recipient_name="Mohamed Nour",  # Same recipient as Ahmed/Fatima ring!
        recipient_account="EG800002000156789012345678901",
        ip_address=IP_MULE_RING, device_fingerprint=FP_FRAUD_RING,
        location="Mumbai, IND", status="pending", is_fraud=True,
        fraud_notes=(
            "Mule account: shares device fingerprint with Ahmed/Fatima ring "
            "(CUST-013/014). Same recipient 'Mohamed Nour'. Zero trades, "
            "3-day account, $5000 deposited → $4800 withdrawal. Pass-through."
        ),
        requested_at=NOW, created_at=NOW,
    ))


async def _seed_hassan(s: AsyncSession) -> None:
    """Hassan Al-Rashid — Bonus Abuser.

    Opens account to exploit welcome bonus. 3 micro-trades ($1 each)
    to meet minimum requirement, then withdraws bonus + deposit immediately.
    """
    cid, pm, dev = _id("hassan_r"), _id("hassan_r.pm.visa"), _id("hassan_r.device")
    ip = "185.107.56.33"

    s.add(Customer(
        id=cid, external_id="CUST-021", name="Hassan Al-Rashid",
        email="hassan.alrashid@example.com", country="ARE",
        registration_date=_ago(days=1), created_at=_ago(days=1), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="mastercard",
        last_four="2244", is_verified=True,
        added_at=_ago(days=1), last_used_at=_ago(hours=6), created_at=_ago(days=1),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint="ff99ee88dd77cc66bb55aa4433221100",
        os="iOS 17", browser="Safari Mobile", screen_resolution="1179x2556",
        first_seen_at=_ago(days=1), last_seen_at=_ago(hours=1),
        is_trusted=False, created_at=_ago(days=1),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Dubai, ARE",
        first_seen_at=_ago(days=1), last_seen_at=_ago(hours=1),
        created_at=_ago(days=1),
    ))
    # Deposit + bonus
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid, type="deposit",
        amount=Decimal("500.00"), currency="USD", status="success",
        payment_method_id=pm, ip_address=ip,
        timestamp=_ago(hours=20), created_at=_ago(hours=20),
    ))
    # 3 micro-trades ($1 each) — minimum to meet bonus requirement
    for i in range(3):
        opened = _ago(hours=18 - i)
        s.add(Trade(
            id=uuid.uuid4(), customer_id=cid, instrument="EUR/USD",
            trade_type="buy", amount=Decimal("1.00"), pnl=Decimal("0.01"),
            opened_at=opened, closed_at=opened + timedelta(seconds=10),
            created_at=opened,
        ))
    s.add(Withdrawal(
        id=_id("hassan_r.wd.pending"), customer_id=cid, amount=Decimal("600.00"),
        currency="USD", payment_method_id=pm,
        recipient_name="Hassan Al-Rashid",
        recipient_account="AE070331234567890123456",
        ip_address=ip, device_fingerprint="ff99ee88dd77cc66bb55aa4433221100",
        location="Dubai, ARE", status="pending", is_fraud=True,
        fraud_notes=(
            "Bonus abuse: 1-day account, deposited $500, 3 micro-trades ($1 each "
            "for 10s — minimum to qualify), withdrawing $600 (deposit + bonus). "
            "Instant cash-out pattern."
        ),
        requested_at=NOW, created_at=NOW,
    ))


async def _seed_elena(s: AsyncSession) -> None:
    """Elena Popescu — Synthetic Identity.

    Fake identity assembled from real data. Mismatched country/IP,
    payment from different country. Shares device with Dmitri (CUST-019).
    """
    cid, pm, dev = _id("elena"), _id("elena.pm.visa"), _id("elena.device")
    ip = "203.0.113.42"  # Same IP range as Dmitri's new IP

    s.add(Customer(
        id=cid, external_id="CUST-022", name="Elena Popescu",
        email="elena.popescu@example.com", country="ROU",
        registration_date=_ago(days=1), created_at=_ago(days=1), updated_at=NOW,
    ))
    s.add(PaymentMethod(
        id=pm, customer_id=cid, type="card", provider="visa",
        last_four="8899", is_verified=True,
        added_at=_ago(days=1), last_used_at=_ago(hours=2),
        created_at=_ago(days=1),
    ))
    s.add(Device(
        id=dev, customer_id=cid, fingerprint=FP_ATO_STOLEN,
        os="macOS 14", browser="Chrome 122", screen_resolution="2560x1440",
        first_seen_at=_ago(hours=12), last_seen_at=_ago(hours=1),
        is_trusted=False, created_at=_ago(hours=12),
    ))
    s.add(IPHistory(
        customer_id=cid, ip_address=ip, location="Lagos, NGA",
        first_seen_at=_ago(hours=12), last_seen_at=_ago(hours=1),
        created_at=_ago(hours=12),
    ))
    s.add(Transaction(
        id=uuid.uuid4(), customer_id=cid, type="deposit",
        amount=Decimal("3000.00"), currency="USD", status="success",
        payment_method_id=pm, ip_address=ip,
        timestamp=_ago(hours=10), created_at=_ago(hours=10),
    ))
    # 1 tiny trade to appear legitimate
    s.add(Trade(
        id=uuid.uuid4(), customer_id=cid, instrument="GBP/USD",
        trade_type="sell", amount=Decimal("5.00"), pnl=Decimal("-0.50"),
        opened_at=_ago(hours=8), closed_at=_ago(hours=8) + timedelta(seconds=20),
        created_at=_ago(hours=8),
    ))
    s.add(Withdrawal(
        id=_id("elena.wd.pending"), customer_id=cid, amount=Decimal("2900.00"),
        currency="USD", payment_method_id=pm, recipient_name="Elena Popescu",
        recipient_account="RO49AAAA1B31007593840000",
        ip_address=ip, device_fingerprint=FP_ATO_STOLEN,
        location="Lagos, NGA", status="pending", is_fraud=True,
        fraud_notes=(
            "Synthetic identity: registered as ROU but IP from Lagos, NGA. "
            "Shares device with Dmitri Kozlov (CUST-019) — ATO cluster. "
            "1-day account, 1 token trade ($5, 20s), withdrawing 97% of deposit."
        ),
        requested_at=NOW, created_at=NOW,
    ))
