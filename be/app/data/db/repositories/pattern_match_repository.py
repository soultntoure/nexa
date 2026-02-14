"""
PatternMatch CRUD + query operations.

Contains:
- PatternMatchRepository class (takes AsyncSession)
  - get_current_by_customer(customer_id) -> list[PatternMatch]
  - get_by_pattern(pattern_id) -> list[PatternMatch]
  - bulk_upsert(pattern_id, matches) -> list[PatternMatch]
  - invalidate_current(pattern_id) -> int

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.pattern_match import PatternMatch
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatternMatchRepository(BaseRepository[PatternMatch]):
    """Repository for PatternMatch with customer and pattern queries."""

    model_class = PatternMatch

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_current_by_customer(
        self, customer_id: uuid.UUID,
    ) -> list[PatternMatch]:
        """Get all current (is_current=True) matches for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            List of detached PatternMatch rows
        """
        try:
            stmt = select(PatternMatch).where(
                and_(
                    PatternMatch.customer_id == customer_id,
                    PatternMatch.is_current == True,
                )
            )
            result = await self.session.execute(stmt)
            matches = list(result.scalars().all())
            for m in matches:
                self._expunge(m)
            return matches
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving current matches for customer {customer_id}"
            ) from e

    async def get_by_pattern(self, pattern_id: uuid.UUID) -> list[PatternMatch]:
        """Get all current matches for a given pattern.

        Args:
            pattern_id: UUID of the fraud pattern

        Returns:
            List of detached PatternMatch rows (is_current=True only)
        """
        try:
            stmt = select(PatternMatch).where(
                and_(
                    PatternMatch.pattern_id == pattern_id,
                    PatternMatch.is_current == True,
                )
            )
            result = await self.session.execute(stmt)
            matches = list(result.scalars().all())
            for m in matches:
                self._expunge(m)
            return matches
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving matches for pattern {pattern_id}"
            ) from e

    async def invalidate_current(self, pattern_id: uuid.UUID) -> int:
        """Mark all current matches for a pattern as not current.

        Returns:
            Number of rows updated
        """
        try:
            stmt = (
                update(PatternMatch)
                .where(
                    and_(
                        PatternMatch.pattern_id == pattern_id,
                        PatternMatch.is_current == True,
                    )
                )
                .values(is_current=False)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error invalidating matches for pattern {pattern_id}"
            ) from e

    async def bulk_upsert(
        self,
        pattern_id: uuid.UUID,
        matches: list[PatternMatch],
    ) -> list[PatternMatch]:
        """Replace current matches for a pattern with a new set.

        1. Invalidates all existing current matches for the pattern
        2. Inserts the new match rows

        Args:
            pattern_id: UUID of the fraud pattern
            matches: New PatternMatch instances to insert

        Returns:
            List of created PatternMatch rows (detached)
        """
        try:
            # Invalidate existing current matches
            await self.session.execute(
                update(PatternMatch)
                .where(
                    and_(
                        PatternMatch.pattern_id == pattern_id,
                        PatternMatch.is_current == True,
                    )
                )
                .values(is_current=False)
            )

            # Insert new matches
            created = []
            for match in matches:
                self.session.add(match)

            await self.session.commit()

            for match in matches:
                await self.session.refresh(match)
                self._expunge(match)
                created.append(match)

            return created
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error bulk-upserting matches for pattern {pattern_id}"
            ) from e

    async def count_by_pattern(self, pattern_id: uuid.UUID) -> int:
        """Count current matches for a pattern."""
        try:
            stmt = (
                select(func.count())
                .select_from(PatternMatch)
                .where(
                    and_(
                        PatternMatch.pattern_id == pattern_id,
                        PatternMatch.is_current == True,
                    )
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error counting matches for pattern {pattern_id}"
            ) from e
