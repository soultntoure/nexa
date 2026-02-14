"""
WeightProfileRepository — CRUD for per-customer weight profiles.

Methods:
- get_active(customer_id) -> active profile or None
- deactivate_all(customer_id) -> set is_active=False on all
- save_profile(profile) -> deactivate old, insert new active one

Rules: async only, expunge before return, single transaction for save.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.customer_weight_profile import CustomerWeightProfile
from app.data.db.repositories.base_repository import BaseRepository


class WeightProfileRepository(BaseRepository[CustomerWeightProfile]):
    """Repository for per-customer indicator weight profiles."""

    model_class = CustomerWeightProfile

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_active(
        self, customer_id: uuid.UUID
    ) -> CustomerWeightProfile | None:
        """Get the single active weight profile for a customer."""
        try:
            stmt = select(CustomerWeightProfile).where(
                CustomerWeightProfile.customer_id == customer_id,
                CustomerWeightProfile.is_active.is_(True),
            )
            result = await self.session.execute(stmt)
            profile = result.scalar_one_or_none()
            if profile:
                self._expunge(profile)
            return profile
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting active profile for customer {customer_id}"
            ) from e

    async def deactivate_all(self, customer_id: uuid.UUID) -> None:
        """Set is_active=False on all profiles for a customer."""
        try:
            stmt = (
                update(CustomerWeightProfile)
                .where(
                    CustomerWeightProfile.customer_id == customer_id,
                    CustomerWeightProfile.is_active.is_(True),
                )
                .values(is_active=False)
            )
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error deactivating profiles for customer {customer_id}"
            ) from e

    async def save_profile(
        self, profile: CustomerWeightProfile
    ) -> CustomerWeightProfile:
        """Deactivate old profiles, insert new active one. Single transaction."""
        try:
            await self.deactivate_all(profile.customer_id)
            self.session.add(profile)
            await self.session.commit()
            await self.session.refresh(profile)
            self._expunge(profile)
            return profile
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error saving profile for customer {profile.customer_id}"
            ) from e
