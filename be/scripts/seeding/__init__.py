"""Seeding package — exports SCENARIO_SEEDERS and TABLES_TO_TRUNCATE."""

from .admins import _seed_admins
from .audit_patterns import _seed_audit_patterns
from .clean_customers import (
    _seed_aisha, _seed_emma, _seed_james, _seed_kenji, _seed_raj, _seed_sarah,
)
from .escalate_customers import _seed_david, _seed_maria, _seed_tom, _seed_yuki
from .fraud_customers import (
    _seed_ahmed_and_fatima, _seed_carlos, _seed_nina, _seed_sophie, _seed_victor,
)
from .fraud_customers_extra import _seed_liam, _seed_olga, _seed_dmitri
from .fraud_customers_extra2 import _seed_priya, _seed_hassan, _seed_elena
from .fraud_evaluations_orig import _seed_evaluations_orig
from .fraud_evaluations_extra import _seed_evaluations_extra
from .threshold_config import _seed_threshold
from .weight_profiles import _seed_weight_profiles

TABLES_TO_TRUNCATE = [
    "audit_candidate_evidence",
    "audit_text_units",
    "audit_candidates",
    "audit_runs",
    "evaluations",
    "feedback",
    "indicator_results",
    "withdrawal_decisions",
    "alerts",
    "admins",
    "withdrawals",
    "trades",
    "transactions",
    "ip_history",
    "devices",
    "payment_methods",
    "customer_weight_profiles",
    "customers",
    "threshold_config",
    "fraud_patterns",
    "customer_risk_postures",
]

SCENARIO_SEEDERS = [
    # Admin identities (for traceability)
    ("Admin Identities", _seed_admins),
    # Clean (expected: APPROVE)
    ("Sarah Chen — Reliable Regular", _seed_sarah),
    ("James Wilson — VIP Whale", _seed_james),
    ("Aisha Mohammed — E-Wallet Loyalist", _seed_aisha),
    ("Kenji Sato — Crypto Consistent", _seed_kenji),
    ("Emma Davies — Low-Volume Veteran", _seed_emma),
    ("Raj Patel — Premium Trader", _seed_raj),
    # Medium risk (expected: ESCALATE)
    ("David Park — Business Traveler", _seed_david),
    ("Maria Santos — New High-Roller", _seed_maria),
    ("Tom Brown — Method Switcher", _seed_tom),
    ("Yuki Tanaka — Dormant Returner", _seed_yuki),
    # Fraud (expected: BLOCK) — original 5
    ("Victor Petrov — No-Trade Fraudster", _seed_victor),
    ("Sophie Laurent — Card Tester", _seed_sophie),
    ("Ahmed & Fatima — Fraud Ring", _seed_ahmed_and_fatima),
    ("Carlos Mendez — Velocity Abuser", _seed_carlos),
    ("Nina Volkov — Geo Impossible", _seed_nina),
    # Fraud (expected: BLOCK) — extra 6
    ("Liam Chen — Refund Abuser", _seed_liam),
    ("Olga Ivanova — Smurfing / Structuring", _seed_olga),
    ("Dmitri Kozlov — Account Takeover", _seed_dmitri),
    ("Priya Sharma — Mule Account", _seed_priya),
    ("Hassan Al-Rashid — Bonus Abuser", _seed_hassan),
    ("Elena Popescu — Synthetic Identity", _seed_elena),
    # Weight profiles (after all customers, before config)
    ("Customer Weight Profiles", _seed_weight_profiles),
    # Config
    ("Threshold Config", _seed_threshold),
    # Evaluations for fraud customers (needed for audit text unit FKs)
    ("Evaluations — Original Fraud (CUST-011–016)", _seed_evaluations_orig),
    ("Evaluations — Extra Fraud (CUST-017–022)", _seed_evaluations_extra),
    # Background audit demo data (after evaluations exist)
    ("Audit Patterns (3 candidates + evidence)", _seed_audit_patterns),
]
