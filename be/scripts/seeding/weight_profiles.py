"""Seed customer weight profiles — personalized indicator weights from feedback."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.customer_weight_profile import CustomerWeightProfile

from .constants import _ago, _id


def _default_weights(**overrides: dict) -> dict:
    """Build indicator_weights dict with defaults + overrides."""
    defaults = {
        "amount_anomaly": {"multiplier": 1.0, "reason": ""},
        "velocity": {"multiplier": 1.0, "reason": ""},
        "geographic": {"multiplier": 1.0, "reason": ""},
        "trading_behavior": {"multiplier": 1.0, "reason": ""},
        "device_fingerprint": {"multiplier": 1.0, "reason": ""},
        "payment_method": {"multiplier": 1.0, "reason": ""},
        "recipient": {"multiplier": 1.0, "reason": ""},
        "card_errors": {"multiplier": 1.0, "reason": ""},
    }
    defaults.update(overrides)
    return defaults


async def _seed_weight_profiles(s: AsyncSession) -> None:
    """Seed 16 customer weight profiles based on officer decision history."""
    profiles = [
        CustomerWeightProfile(
            id=_id("james.weight_profile"), customer_id=_id("james"),
            indicator_weights=_default_weights(
                amount_anomaly={"multiplier": 0.65, "reason": "Officer approved repeated $10k-15k withdrawals — large amounts normal for VIP"},
                velocity={"multiplier": 1.15, "reason": "Occasional same-day double withdrawals flagged by officers"},
                trading_behavior={"multiplier": 0.85, "reason": "150+ trades in history — heavy trading is baseline for this customer"},
            ),
            blend_weights={"rule_engine": 0.65, "investigators": 0.35},
            decision_window=[
                {"decision": "approved", "score": s} for s in
                [0.12, 0.15, 0.18, 0.11, 0.14, 0.22, 0.13, 0.16, 0.19, 0.12, 0.14, 0.17]
            ],
            is_active=True, recalculated_at=_ago(days=3), created_at=_ago(days=45),
        ),
        CustomerWeightProfile(
            id=_id("raj.weight_profile"), customer_id=_id("raj"),
            indicator_weights=_default_weights(
                geographic={"multiplier": 0.75, "reason": "Indian IP ranges look noisy but officers consistently approved — suppressed"},
                amount_anomaly={"multiplier": 0.9, "reason": "$2k-4k range is normal for this premium trader"},
                trading_behavior={"multiplier": 0.8, "reason": "120+ trades — officers confirmed heavy activity is legitimate"},
                device_fingerprint={"multiplier": 1.1, "reason": "Browser upgrade caused one false flag — slight bump retained"},
            ),
            blend_weights={"rule_engine": 0.6, "investigators": 0.4},
            decision_window=[
                {"decision": "approved", "score": 0.15}, {"decision": "approved", "score": 0.18},
                {"decision": "approved", "score": 0.12}, {"decision": "escalated", "score": 0.35},
                {"decision": "approved", "score": 0.14}, {"decision": "approved", "score": 0.16},
                {"decision": "approved", "score": 0.13}, {"decision": "approved", "score": 0.19},
                {"decision": "approved", "score": 0.11}, {"decision": "approved", "score": 0.17},
            ],
            is_active=True, recalculated_at=_ago(days=5), created_at=_ago(days=60),
        ),
        CustomerWeightProfile(
            id=_id("david.weight_profile"), customer_id=_id("david"),
            indicator_weights=_default_weights(
                geographic={"multiplier": 0.6, "reason": "VPN + multi-country flagged every time but officers approved — heavily suppressed"},
                device_fingerprint={"multiplier": 1.25, "reason": "Officers rely on device consistency as trust anchor for this traveler"},
                velocity={"multiplier": 1.1, "reason": "Withdraws right after landing in new countries — officers watch this"},
                trading_behavior={"multiplier": 0.95, "reason": ""},
            ),
            blend_weights={"rule_engine": 0.5, "investigators": 0.5},
            decision_window=[
                {"decision": "approved", "score": 0.38}, {"decision": "approved", "score": 0.42},
                {"decision": "escalated", "score": 0.51}, {"decision": "approved", "score": 0.35},
                {"decision": "approved", "score": 0.40}, {"decision": "approved", "score": 0.33},
            ],
            is_active=True, recalculated_at=_ago(days=7), created_at=_ago(days=30),
        ),
        CustomerWeightProfile(
            id=_id("yuki.weight_profile"), customer_id=_id("yuki"),
            indicator_weights=_default_weights(
                device_fingerprint={"multiplier": 1.4, "reason": "New device after 6-month dormancy — officers flagged this as key signal"},
                trading_behavior={"multiplier": 1.2, "reason": "Officers want to see resumed trading activity before trusting again"},
                velocity={"multiplier": 0.85, "reason": "Slow and steady withdrawals — not a velocity concern"},
                geographic={"multiplier": 0.95, "reason": "Same city (Osaka) — dormancy not a geo issue"},
            ),
            blend_weights={"rule_engine": 0.55, "investigators": 0.45},
            decision_window=[
                {"decision": "approved", "score": 0.28}, {"decision": "escalated", "score": 0.45},
                {"decision": "approved", "score": 0.32}, {"decision": "escalated", "score": 0.48},
                {"decision": "approved", "score": 0.25},
            ],
            is_active=True, recalculated_at=_ago(days=2), created_at=_ago(days=14),
        ),
        CustomerWeightProfile(
            id=_id("victor.weight_profile"), customer_id=_id("victor"),
            indicator_weights=_default_weights(
                trading_behavior={"multiplier": 1.7, "reason": "No-trade pattern is the primary fraud signal — reinforced by 6 officer blocks"},
                amount_anomaly={"multiplier": 1.3, "reason": "Withdrawing 95%+ of deposit is consistent fraud pattern"},
                recipient={"multiplier": 1.2, "reason": "Third-party recipients on new accounts flagged by officers"},
                card_errors={"multiplier": 0.9, "reason": "Card worked fine for this customer — not the relevant signal"},
                geographic={"multiplier": 1.05, "reason": ""},
            ),
            blend_weights={"rule_engine": 0.55, "investigators": 0.45},
            decision_window=[
                {"decision": "blocked", "score": 0.82}, {"decision": "blocked", "score": 0.78},
                {"decision": "escalated", "score": 0.65}, {"decision": "blocked", "score": 0.85},
                {"decision": "blocked", "score": 0.80}, {"decision": "escalated", "score": 0.62},
                {"decision": "blocked", "score": 0.88}, {"decision": "blocked", "score": 0.84},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=4),
        ),
        CustomerWeightProfile(
            id=_id("carlos.weight_profile"), customer_id=_id("carlos"),
            indicator_weights=_default_weights(
                velocity={"multiplier": 1.9, "reason": "5 withdrawals in 1 hour is THE defining fraud signal — max reinforcement by officers"},
                device_fingerprint={"multiplier": 1.5, "reason": "3 different devices used in rapid succession — strong cross-signal"},
                geographic={"multiplier": 1.2, "reason": "VPN usage combined with velocity is a compound fraud indicator"},
                trading_behavior={"multiplier": 0.8, "reason": "Has some legit trades — this indicator misleads for velocity abusers"},
                amount_anomaly={"multiplier": 1.05, "reason": ""},
            ),
            blend_weights={"rule_engine": 0.6, "investigators": 0.4},
            decision_window=[
                {"decision": "blocked", "score": 0.75}, {"decision": "blocked", "score": 0.82},
                {"decision": "escalated", "score": 0.58}, {"decision": "blocked", "score": 0.79},
                {"decision": "blocked", "score": 0.85}, {"decision": "escalated", "score": 0.61},
                {"decision": "blocked", "score": 0.88},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=10),
        ),
        CustomerWeightProfile(
            id=_id("sarah.weight_profile"), customer_id=_id("sarah"),
            indicator_weights=_default_weights(
                amount_anomaly={"multiplier": 0.92, "reason": "Consistent $200-800 range, slightly over-flagged historically"},
                velocity={"multiplier": 0.95, "reason": "Regular monthly withdrawals, no spikes"},
            ),
            blend_weights={"rule_engine": 0.6, "investigators": 0.4},
            decision_window=[
                {"decision": "approved", "score": s} for s in
                [0.08, 0.12, 0.10, 0.15, 0.09, 0.18, 0.11, 0.14]
            ],
            is_active=True, recalculated_at=_ago(days=10), created_at=_ago(days=90),
        ),
        CustomerWeightProfile(
            id=_id("aisha.weight_profile"), customer_id=_id("aisha"),
            indicator_weights=_default_weights(
                payment_method={"multiplier": 0.88, "reason": "Skrill e-wallet consistently approved, lower risk than card for this customer"},
                amount_anomaly={"multiplier": 0.93, "reason": "Small amounts ($100-400) always clean"},
            ),
            blend_weights={"rule_engine": 0.6, "investigators": 0.4},
            decision_window=[
                {"decision": "approved", "score": s} for s in [0.06, 0.10, 0.08, 0.14, 0.09, 0.12]
            ],
            is_active=True, recalculated_at=_ago(days=12), created_at=_ago(days=60),
        ),
        CustomerWeightProfile(
            id=_id("kenji.weight_profile"), customer_id=_id("kenji"),
            indicator_weights=_default_weights(
                payment_method={"multiplier": 0.85, "reason": "Crypto withdrawals to same BTC wallet always approved — suppressed"},
                recipient={"multiplier": 0.9, "reason": "Same recipient wallet every time, officers trust it"},
                trading_behavior={"multiplier": 0.95, "reason": "Active trader, slightly over-flagged"},
            ),
            blend_weights={"rule_engine": 0.6, "investigators": 0.4},
            decision_window=[
                {"decision": "approved", "score": s} for s in [0.09, 0.12, 0.11, 0.16, 0.10, 0.14, 0.13]
            ],
            is_active=True, recalculated_at=_ago(days=8), created_at=_ago(days=75),
        ),
        CustomerWeightProfile(
            id=_id("emma.weight_profile"), customer_id=_id("emma"),
            indicator_weights=_default_weights(
                velocity={"multiplier": 0.8, "reason": "Very infrequent withdrawals flagged as unusual — officers learned this is her pattern"},
                amount_anomaly={"multiplier": 0.9, "reason": "Small amounts ($50-250) always fine"},
                trading_behavior={"multiplier": 1.1, "reason": "Low trading volume is actually worth watching for account changes"},
            ),
            blend_weights={"rule_engine": 0.62, "investigators": 0.38},
            decision_window=[
                {"decision": "approved", "score": s} for s in [0.07, 0.11, 0.09, 0.15, 0.10]
            ],
            is_active=True, recalculated_at=_ago(days=15), created_at=_ago(days=120),
        ),
        CustomerWeightProfile(
            id=_id("maria.weight_profile"), customer_id=_id("maria"),
            indicator_weights=_default_weights(
                amount_anomaly={"multiplier": 1.35, "reason": "First withdrawal was 5x average — officers flagged amount as key concern"},
                trading_behavior={"multiplier": 1.15, "reason": "Only 15 trades in 3 weeks — officers want more activity before trusting"},
                payment_method={"multiplier": 1.1, "reason": "New bank transfer method added 2 days before withdrawal"},
            ),
            blend_weights={"rule_engine": 0.58, "investigators": 0.42},
            decision_window=[
                {"decision": "escalated", "score": 0.45}, {"decision": "escalated", "score": 0.52},
                {"decision": "approved", "score": 0.28},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=5),
        ),
        CustomerWeightProfile(
            id=_id("tom.weight_profile"), customer_id=_id("tom"),
            indicator_weights=_default_weights(
                payment_method={"multiplier": 1.4, "reason": "Switched from card to crypto — officers want extra scrutiny on new methods"},
                recipient={"multiplier": 1.15, "reason": "New BTC wallet address never seen before"},
                trading_behavior={"multiplier": 0.9, "reason": "45 trades over a year, solid history"},
            ),
            blend_weights={"rule_engine": 0.58, "investigators": 0.42},
            decision_window=[
                {"decision": "approved", "score": 0.12}, {"decision": "approved", "score": 0.15},
                {"decision": "approved", "score": 0.18}, {"decision": "escalated", "score": 0.42},
            ],
            is_active=True, recalculated_at=_ago(days=2), created_at=_ago(days=15),
        ),
        CustomerWeightProfile(
            id=_id("sophie.weight_profile"), customer_id=_id("sophie"),
            indicator_weights=_default_weights(
                card_errors={"multiplier": 1.55, "reason": "3 failed cards before success — strong fraud signal confirmed by officers"},
                trading_behavior={"multiplier": 1.3, "reason": "Minimal trading confirms deposit-and-withdraw pattern"},
                device_fingerprint={"multiplier": 1.15, "reason": "Shared device with Victor adds cross-account risk"},
            ),
            blend_weights={"rule_engine": 0.55, "investigators": 0.45},
            decision_window=[
                {"decision": "blocked", "score": 0.78}, {"decision": "escalated", "score": 0.62},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=3),
        ),
        CustomerWeightProfile(
            id=_id("ahmed.weight_profile"), customer_id=_id("ahmed"),
            indicator_weights=_default_weights(
                recipient={"multiplier": 1.45, "reason": "Third-party recipient 'Mohamed Nour' shared across accounts — key ring signal"},
                trading_behavior={"multiplier": 1.4, "reason": "Single token trade ($20, 45s) — classic no-trade fraud"},
                device_fingerprint={"multiplier": 1.25, "reason": "Shared device with Fatima confirms ring operation"},
            ),
            blend_weights={"rule_engine": 0.55, "investigators": 0.45},
            decision_window=[
                {"decision": "blocked", "score": 0.82}, {"decision": "blocked", "score": 0.85},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=2),
        ),
        CustomerWeightProfile(
            id=_id("fatima.weight_profile"), customer_id=_id("fatima"),
            indicator_weights=_default_weights(
                recipient={"multiplier": 1.5, "reason": "Same third-party recipient as Ahmed — strongest ring indicator"},
                trading_behavior={"multiplier": 1.6, "reason": "ZERO trades — worse than Ahmed, pure deposit-and-withdraw"},
                device_fingerprint={"multiplier": 1.25, "reason": "Shared device with Ahmed"},
                geographic={"multiplier": 1.1, "reason": "Same IP as Ahmed from Cairo"},
            ),
            blend_weights={"rule_engine": 0.55, "investigators": 0.45},
            decision_window=[
                {"decision": "blocked", "score": 0.85}, {"decision": "blocked", "score": 0.88},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=2),
        ),
        CustomerWeightProfile(
            id=_id("nina.weight_profile"), customer_id=_id("nina"),
            indicator_weights=_default_weights(
                geographic={"multiplier": 1.45, "reason": "Kyiv to São Paulo in 5 minutes — impossible travel is THE signal"},
                device_fingerprint={"multiplier": 1.3, "reason": "New device appeared at impossible destination"},
                amount_anomaly={"multiplier": 1.2, "reason": "$2000 is 4x her normal range"},
            ),
            blend_weights={"rule_engine": 0.55, "investigators": 0.45},
            decision_window=[
                {"decision": "blocked", "score": 0.80}, {"decision": "blocked", "score": 0.86},
                {"decision": "escalated", "score": 0.58},
            ],
            is_active=True, recalculated_at=_ago(days=1), created_at=_ago(days=5),
        ),
    ]
    s.add_all(profiles)
