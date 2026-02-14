"""
Repository layer exports.

Provides clean imports for all active repository classes.
"""

from app.data.db.repositories.base_repository import BaseRepository

# Core Entity Repositories
from app.data.db.repositories.customer_repository import CustomerRepository
from app.data.db.repositories.withdrawal_repository import WithdrawalRepository
from app.data.db.repositories.transaction_repository import TransactionRepository
from app.data.db.repositories.payment_method_repository import PaymentMethodRepository

# Supporting Entity Repositories
from app.data.db.repositories.device_repository import DeviceRepository
from app.data.db.repositories.ip_history_repository import IPHistoryRepository
from app.data.db.repositories.trade_repository import TradeRepository
from app.data.db.repositories.alert_repository import AlertRepository

# Decision & Analytics Repositories
from app.data.db.repositories.withdrawal_decision_repository import WithdrawalDecisionRepository
from app.data.db.repositories.indicator_result_repository import IndicatorResultRepository
from app.data.db.repositories.threshold_config_repository import ThresholdConfigRepository
from app.data.db.repositories.fraud_pattern_repository import CustomerFraudSignalRepository
from app.data.db.repositories.weight_profile_repository import WeightProfileRepository

# Pre-Fraud Posture
from app.data.db.repositories.posture_repository import PostureRepository

# Phase 2 — Pattern Discovery
from app.data.db.repositories.pattern_repository import PatternRepository
from app.data.db.repositories.pattern_match_repository import PatternMatchRepository

__all__ = [
    # Base
    "BaseRepository",
    # Core
    "CustomerRepository",
    "WithdrawalRepository",
    "TransactionRepository",
    "PaymentMethodRepository",
    # Supporting
    "DeviceRepository",
    "IPHistoryRepository",
    "TradeRepository",
    "AlertRepository",
    # Decision & Analytics
    "WithdrawalDecisionRepository",
    "IndicatorResultRepository",
    "ThresholdConfigRepository",
    "CustomerFraudSignalRepository",
    "WeightProfileRepository",
    # Pre-Fraud Posture
    "PostureRepository",
    # Phase 2 — Pattern Discovery
    "PatternRepository",
    "PatternMatchRepository",
]
