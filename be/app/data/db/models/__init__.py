"""
SQLAlchemy models — import all models here for Alembic discovery.

Re-exports:
- Admin
- Customer, Transaction, PaymentMethod, Trade
- Withdrawal, WithdrawalDecision, IndicatorResult
- Alert, Device, IPHistory
- Feedback, CustomerFraudSignal, FraudPattern, PatternMatch, ThresholdConfig
- CustomerRiskPosture, CustomerWeightProfile
"""

from app.data.db.models.admin import Admin
from app.data.db.models.alert import Alert
from app.data.db.models.audit_candidate import AuditCandidate
from app.data.db.models.audit_config import AuditConfig
from app.data.db.models.audit_candidate_evidence import AuditCandidateEvidence
from app.data.db.models.audit_run import AuditRun
from app.data.db.models.audit_text_unit import AuditTextUnit
from app.data.db.models.customer import Customer
from app.data.db.models.customer_fraud_signal import CustomerFraudSignal
from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.data.db.models.customer_weight_profile import CustomerWeightProfile
from app.data.db.models.evaluation import Evaluation
from app.data.db.models.device import Device
from app.data.db.models.feedback import Feedback
from app.data.db.models.fraud_pattern import FraudPattern
from app.data.db.models.indicator_result import IndicatorResult
from app.data.db.models.ip_history import IPHistory
from app.data.db.models.pattern_match import PatternMatch
from app.data.db.models.payment_method import PaymentMethod
from app.data.db.models.threshold_config import ThresholdConfig
from app.data.db.models.trade import Trade
from app.data.db.models.transaction import Transaction
from app.data.db.models.withdrawal import Withdrawal
from app.data.db.models.withdrawal_decision import WithdrawalDecision

__all__ = [
    "Admin",
    "Alert",
    "AuditCandidate",
    "AuditCandidateEvidence",
    "AuditConfig",
    "AuditRun",
    "AuditTextUnit",
    "Customer",
    "CustomerFraudSignal",
    "CustomerRiskPosture",
    "CustomerWeightProfile",
    "Evaluation",
    "Device",
    "Feedback",
    "FraudPattern",
    "IPHistory",
    "IndicatorResult",
    "PatternMatch",
    "PaymentMethod",
    "ThresholdConfig",
    "Trade",
    "Transaction",
    "Withdrawal",
    "WithdrawalDecision",
]
