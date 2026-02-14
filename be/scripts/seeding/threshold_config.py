"""Seed threshold configuration."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models import ThresholdConfig

from .constants import _id


async def _seed_threshold(s: AsyncSession) -> None:
    """Seed the initial threshold config with default weights."""
    s.add(ThresholdConfig(
        id=_id("threshold.default"),
        approve_below=30.0,
        escalate_below=70.0,
        indicator_weights={
            "payment_method": 1.0,
            "amount_anomaly": 1.0,
            "geographic": 1.2,
            "trading_behavior": 1.5,
            "velocity": 1.0,
            "device_fingerprint": 1.3,
            "recipient": 1.0,
            "card_errors": 1.2,
        },
        updated_by="system",
        reason="Initial default thresholds",
        is_active=True,
    ))
