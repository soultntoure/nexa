"""
Pattern Match signal — scores customers against active fraud patterns.

Checks pattern_matches joined with fraud_patterns for current, active matches.
When PATTERN_SCORING_ENABLED is False (shadow mode), returns zero score.
When enabled, score = min(max_confidence, 0.85).

Inputs: pattern_matches, fraud_patterns (state='active', is_current=True)
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.data.db.models.fraud_pattern import FraudPattern
from app.data.db.models.pattern_match import PatternMatch
from app.services.prefraud.signals.base import BaseSignal, SignalResult


class PatternMatchSignal(BaseSignal):
    """Scores customer based on active fraud pattern matches."""

    name = "pattern_match"

    async def compute(
        self, customer_id: uuid.UUID, session: AsyncSession,
    ) -> SignalResult:
        settings = get_settings()

        if not settings.PATTERN_SCORING_ENABLED:
            return SignalResult(
                name=self.name,
                score=0.0,
                evidence={},
                reason="Pattern scoring disabled (shadow mode)",
            )

        matches = await session.execute(
            select(PatternMatch)
            .join(FraudPattern)
            .options(joinedload(PatternMatch.pattern))
            .where(
                PatternMatch.customer_id == customer_id,
                PatternMatch.is_current == True,  # noqa: E712
                FraudPattern.state == "active",
            )
        )
        rows = matches.scalars().unique().all()

        if not rows:
            return SignalResult(
                name=self.name,
                score=0.0,
                evidence={},
                reason="No active pattern matches",
            )

        max_confidence = max(r.confidence for r in rows)
        score = min(max_confidence, 0.85)

        reason = f"Matches {len(rows)} active fraud pattern(s)"
        evidence = {
            "matched_patterns": [
                {
                    "pattern_type": r.pattern.pattern_type,
                    "confidence": r.confidence,
                    "pattern_id": str(r.pattern_id),
                }
                for r in rows
            ],
            "match_count": len(rows),
        }

        return SignalResult(
            name=self.name,
            score=score,
            evidence=evidence,
            reason=reason,
        )
