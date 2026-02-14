"""
CustomerFraudSignal CRUD operations.

Renamed from FraudPatternRepository (Phase 1) to match the renamed
CustomerFraudSignal model.

Contains:
- CustomerFraudSignalRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> CustomerFraudSignal | None
  - get_by_pattern_type(pattern_type: str) -> list[CustomerFraudSignal]
  - get_high_confidence(threshold: float, limit: int) -> list[CustomerFraudSignal]
  - increment_frequency(id: UUID) -> CustomerFraudSignal
  - get_recent(limit: int) -> list[CustomerFraudSignal]

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.customer_fraud_signal import CustomerFraudSignal
from app.data.db.repositories.base_repository import BaseRepository


class CustomerFraudSignalRepository(BaseRepository[CustomerFraudSignal]):
    """Repository for CustomerFraudSignal entity with pattern detection and analysis."""

    model_class = CustomerFraudSignal

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_pattern_type(self, pattern_type: str) -> list[CustomerFraudSignal]:
        """
        Get all signals of a specific type.

        Args:
            pattern_type: Type of fraud pattern

        Returns:
            List of detached CustomerFraudSignals
        """
        try:
            stmt = select(CustomerFraudSignal).where(
                CustomerFraudSignal.pattern_type == pattern_type
            )
            result = await self.session.execute(stmt)
            patterns = list(result.scalars().all())

            for pattern in patterns:
                self._expunge(pattern)

            return patterns
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving signals of type {pattern_type}"
            ) from e

    async def get_high_confidence(
        self, threshold: float = 0.7, limit: int = 50
    ) -> list[CustomerFraudSignal]:
        """
        Get fraud signals with confidence above threshold.

        Args:
            threshold: Confidence threshold (0.0-1.0)
            limit: Maximum number of signals to return

        Returns:
            List of detached high-confidence CustomerFraudSignals
        """
        try:
            stmt = (
                select(CustomerFraudSignal)
                .where(CustomerFraudSignal.confidence >= threshold)
                .order_by(desc(CustomerFraudSignal.confidence))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            patterns = list(result.scalars().all())

            for pattern in patterns:
                self._expunge(pattern)

            return patterns
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving high confidence signals") from e

    async def increment_frequency(self, id: uuid.UUID) -> CustomerFraudSignal | None:
        """
        Increment the frequency counter for a signal when detected again.

        Args:
            id: UUID of the fraud signal

        Returns:
            Updated CustomerFraudSignal (detached), None if not found
        """
        try:
            pattern = await self.session.get(CustomerFraudSignal, id)
            if not pattern:
                return None

            pattern.frequency += 1
            await self.session.commit()
            await self.session.refresh(pattern)
            self._expunge(pattern)

            return pattern
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error incrementing frequency for signal {id}"
            ) from e

    async def get_recent(self, limit: int = 50) -> list[CustomerFraudSignal]:
        """
        Get recently detected fraud signals.

        Args:
            limit: Maximum number of signals to return

        Returns:
            List of detached CustomerFraudSignals, most recent first
        """
        try:
            stmt = (
                select(CustomerFraudSignal)
                .order_by(desc(CustomerFraudSignal.detected_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            patterns = list(result.scalars().all())

            for pattern in patterns:
                self._expunge(pattern)

            return patterns
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving recent fraud signals") from e

    async def get_by_customer_and_type(
        self, customer_id: uuid.UUID, signal_type: str,
    ) -> list[CustomerFraudSignal]:
        """Get all signals for a customer filtered by signal type."""
        try:
            stmt = select(CustomerFraudSignal).where(
                and_(
                    CustomerFraudSignal.customer_id == customer_id,
                    CustomerFraudSignal.signal_type == signal_type,
                )
            )
            result = await self.session.execute(stmt)
            patterns = list(result.scalars().all())
            for pattern in patterns:
                self._expunge(pattern)
            return patterns
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting signals for customer {customer_id}"
            ) from e

    async def find_matching_pattern(
        self, indicator_combination: list[str], signal_type: str,
    ) -> CustomerFraudSignal | None:
        """Find existing signal with same indicators and signal type.

        Used to increment frequency instead of creating duplicates.
        """
        try:
            stmt = select(CustomerFraudSignal).where(
                and_(
                    CustomerFraudSignal.indicator_combination == sorted(indicator_combination),
                    CustomerFraudSignal.signal_type == signal_type,
                )
            )
            result = await self.session.execute(stmt)
            pattern = result.scalar_one_or_none()
            if pattern:
                self._expunge(pattern)
            return pattern
        except SQLAlchemyError as e:
            raise RuntimeError(
                "Error finding matching signal"
            ) from e
