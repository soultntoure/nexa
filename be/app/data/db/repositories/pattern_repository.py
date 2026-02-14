"""
FraudPattern (Phase 2) CRUD + lifecycle operations.

Contains:
- PatternRepository class (takes AsyncSession)
  - get_by_state(state: str) -> list[FraudPattern]
  - get_by_type_and_state(pattern_type, states) -> list[FraudPattern]
  - activate(id, activated_by) -> FraudPattern
  - disable(id, disabled_by, reason) -> FraudPattern
  - update_last_matched(id) -> None
  - increment_frequency(id) -> FraudPattern | None

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.fraud_pattern import FraudPattern
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatternRepository(BaseRepository[FraudPattern]):
    """Repository for Phase 2 FraudPattern with lifecycle management."""

    model_class = FraudPattern

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_state(self, state: str) -> list[FraudPattern]:
        """Get all patterns in a given lifecycle state."""
        try:
            stmt = (
                select(FraudPattern)
                .where(FraudPattern.state == state)
                .order_by(desc(FraudPattern.detected_at))
            )
            result = await self.session.execute(stmt)
            patterns = list(result.scalars().all())
            for p in patterns:
                self._expunge(p)
            return patterns
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving patterns with state {state}"
            ) from e

    async def get_by_type_and_state(
        self,
        pattern_type: str,
        states: list[str],
    ) -> list[FraudPattern]:
        """Get patterns of a given type in any of the specified states."""
        try:
            stmt = (
                select(FraudPattern)
                .where(
                    FraudPattern.pattern_type == pattern_type,
                    FraudPattern.state.in_(states),
                )
                .order_by(desc(FraudPattern.detected_at))
            )
            result = await self.session.execute(stmt)
            patterns = list(result.scalars().all())
            for p in patterns:
                self._expunge(p)
            return patterns
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving patterns of type {pattern_type}"
            ) from e

    async def activate(
        self,
        id: uuid.UUID,
        activated_by: uuid.UUID | None = None,
    ) -> FraudPattern:
        """Transition a pattern to ACTIVE state.

        Args:
            id: Pattern UUID
            activated_by: UUID of the analyst/user who activated

        Returns:
            Updated FraudPattern (detached)

        Raises:
            ValueError: If pattern not found or already active
        """
        try:
            pattern = await self.session.get(FraudPattern, id)
            if not pattern:
                raise ValueError(f"Pattern {id} not found")
            if pattern.state == "active":
                raise ValueError(f"Pattern {id} is already active")

            pattern.state = "active"
            pattern.activated_at = _utcnow()
            pattern.activated_by = activated_by

            await self.session.commit()
            await self.session.refresh(pattern)
            self._expunge(pattern)
            return pattern
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error activating pattern {id}"
            ) from e

    async def disable(
        self,
        id: uuid.UUID,
        disabled_by: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> FraudPattern:
        """Transition a pattern to DISABLED state.

        Args:
            id: Pattern UUID
            disabled_by: UUID of the analyst/user who disabled
            reason: Optional explanation for disabling

        Returns:
            Updated FraudPattern (detached)

        Raises:
            ValueError: If pattern not found or already disabled
        """
        try:
            pattern = await self.session.get(FraudPattern, id)
            if not pattern:
                raise ValueError(f"Pattern {id} not found")
            if pattern.state == "disabled":
                raise ValueError(f"Pattern {id} is already disabled")

            pattern.state = "disabled"
            pattern.disabled_at = _utcnow()
            pattern.disabled_by = disabled_by
            pattern.disabled_reason = reason

            await self.session.commit()
            await self.session.refresh(pattern)
            self._expunge(pattern)
            return pattern
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error disabling pattern {id}"
            ) from e

    async def update_last_matched(self, id: uuid.UUID) -> None:
        """Update the last_matched_at timestamp for a pattern."""
        try:
            pattern = await self.session.get(FraudPattern, id)
            if pattern:
                pattern.last_matched_at = _utcnow()
                await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error updating last_matched_at for pattern {id}"
            ) from e

    async def increment_frequency(self, id: uuid.UUID) -> FraudPattern | None:
        """Increment the frequency counter for a pattern."""
        try:
            pattern = await self.session.get(FraudPattern, id)
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
                f"Error incrementing frequency for pattern {id}"
            ) from e
