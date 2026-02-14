"""Output schema for indicator agents.

Every indicator agent (amount_anomaly, velocity, payment_method, etc.)
returns an IndicatorResult as its structured output.
"""

from typing import Literal

from pydantic import BaseModel, Field

IndicatorName = Literal[
    "amount_anomaly",
    "velocity",
    "payment_method",
    "geographic",
    "device_fingerprint",
    "trading_behavior",
    "recipient",
    "card_errors",
]


class IndicatorResult(BaseModel):
    """Structured output returned by each indicator agent."""

    indicator_name: IndicatorName = Field(
        ...,
        description=(
            "Exact canonical name. Must be one of: "
            "amount_anomaly, velocity, payment_method, geographic, "
            "device_fingerprint, trading_behavior, recipient, card_errors."
        ),
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risk score: 0.0 = safe, 1.0 = high risk.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How certain the agent is in this score.",
    )
    reasoning: str = Field(
        ...,
        max_length=1000,
        description="Brief explanation of the key finding (1-3 sentences).",
    )
    evidence: dict[str, object] = Field(
        default_factory=dict,
        description="Supporting data points (e.g. {'z_score': 2.4, 'count_24h': 7}).",
    )
