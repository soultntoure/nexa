"""Shared constants for seed data generation."""

import random
import uuid
from datetime import datetime, timedelta, timezone

# ── Reproducible randomness ──
random.seed(42)

# ── Reference time: "now" for all seed data ──
# Use current time so temporal windows align with DB NOW().
NOW = datetime.now(timezone.utc)


def _ago(**kw: float) -> datetime:
    return NOW - timedelta(**kw)


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"deriv.seed.{name}")


# ── Instruments for trade generation ──
INSTRUMENTS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "BTC/USD", "ETH/USD"]

# ── Shared fingerprints — fraud customers share for cross-account detection ──
FP_SHARED_FRAUD = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"  # Victor <-> Sophie
FP_FRAUD_RING = "deadbeefdeadbeefdeadbeefdeadbeef"  # Ahmed <-> Fatima
IP_FRAUD_RING = "41.44.55.66"  # Ahmed <-> Fatima

# ── New fraud customers (CUST-017 to CUST-022) ──
FP_ATO_STOLEN = "cc11dd22ee33ff44aa55bb66cc77dd88"  # Dmitri <-> Elena (shared device)
IP_MULE_RING = "41.44.55.77"  # Priya links to Ahmed/Fatima ring
