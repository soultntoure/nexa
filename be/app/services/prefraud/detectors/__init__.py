"""Detector registry — all pattern detectors for the detection service."""

from app.services.prefraud.detectors.card_testing import CardTestingDetector
from app.services.prefraud.detectors.no_trade_withdrawal import (
    NoTradeWithdrawalDetector,
)
from app.services.prefraud.detectors.rapid_funding_cycle import (
    RapidFundingCycleDetector,
)
from app.services.prefraud.detectors.shared_device_ring import (
    SharedDeviceRingDetector,
)
from app.services.prefraud.detectors.velocity_burst import VelocityBurstDetector

ALL_DETECTORS: list[type] = [
    NoTradeWithdrawalDetector,
    SharedDeviceRingDetector,
    RapidFundingCycleDetector,
    VelocityBurstDetector,
    CardTestingDetector,
]

__all__ = [
    "ALL_DETECTORS",
    "CardTestingDetector",
    "NoTradeWithdrawalDetector",
    "RapidFundingCycleDetector",
    "SharedDeviceRingDetector",
    "VelocityBurstDetector",
]
