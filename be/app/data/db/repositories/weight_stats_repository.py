"""WeightStatsRepository — read-only queries on customer_weight_profiles."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.customer_weight_profile import CustomerWeightProfile
from app.data.db.repositories.base_repository import BaseRepository


class WeightStatsRepository(BaseRepository[CustomerWeightProfile]):
    """Read-only statistics queries for weight drift analysis."""

    model_class = CustomerWeightProfile

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_profiles_in_interval(
        self, start: datetime, end: datetime,
    ) -> list[CustomerWeightProfile]:
        """All profiles created in a time window."""
        try:
            stmt = (
                select(CustomerWeightProfile)
                .where(
                    CustomerWeightProfile.created_at >= start,
                    CustomerWeightProfile.created_at <= end,
                )
                .order_by(CustomerWeightProfile.created_at)
            )
            result = await self.session.execute(stmt)
            profiles = list(result.scalars().all())
            for p in profiles:
                self._expunge(p)
            return profiles
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error fetching profiles in interval") from e

    async def get_customer_weight_history(
        self, customer_id: uuid.UUID, limit: int = 20,
    ) -> list[CustomerWeightProfile]:
        """Time-ordered profiles for one customer."""
        try:
            stmt = (
                select(CustomerWeightProfile)
                .where(CustomerWeightProfile.customer_id == customer_id)
                .order_by(CustomerWeightProfile.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            profiles = list(result.scalars().all())
            for p in profiles:
                self._expunge(p)
            return profiles
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error fetching history for {customer_id}") from e

    async def get_all_active_profiles(self) -> list[CustomerWeightProfile]:
        """All currently active profiles (snapshot)."""
        try:
            stmt = (
                select(CustomerWeightProfile)
                .where(CustomerWeightProfile.is_active.is_(True))
            )
            result = await self.session.execute(stmt)
            profiles = list(result.scalars().all())
            for p in profiles:
                self._expunge(p)
            return profiles
        except SQLAlchemyError as e:
            raise RuntimeError("Error fetching active profiles") from e

    async def count_recalculations_in_interval(
        self, start: datetime, end: datetime,
    ) -> int:
        """Count of recalibrations in window."""
        try:
            stmt = (
                select(func.count())
                .select_from(CustomerWeightProfile)
                .where(
                    CustomerWeightProfile.created_at >= start,
                    CustomerWeightProfile.created_at <= end,
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError as e:
            raise RuntimeError("Error counting recalculations") from e
