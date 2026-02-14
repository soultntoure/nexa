"""
CustomerRiskPosture CRUD + posture-specific queries.

Contains:
- PostureRepository class (takes AsyncSession)
  - get_current(customer_id: UUID) -> CustomerRiskPosture | None
  - save_snapshot(posture: CustomerRiskPosture) -> CustomerRiskPosture
  - get_history(customer_id, limit, offset) -> list[CustomerRiskPosture]
  - count_history(customer_id: UUID) -> int
  - get_all_current() -> list[CustomerRiskPosture]

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.customer_risk_posture import CustomerRiskPosture
from app.data.db.repositories.base_repository import BaseRepository


class PostureRepository(BaseRepository[CustomerRiskPosture]):
    """Repository for CustomerRiskPosture with posture-specific queries."""

    model_class = CustomerRiskPosture

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_current(self, customer_id: uuid.UUID) -> CustomerRiskPosture | None:
        """
        Get the current (most recent active) posture for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            Detached CustomerRiskPosture if found, None otherwise
        """
        try:
            stmt = select(CustomerRiskPosture).where(
                and_(
                    CustomerRiskPosture.customer_id == customer_id,
                    CustomerRiskPosture.is_current == True,
                )
            )
            result = await self.session.execute(stmt)
            posture = result.scalar_one_or_none()

            if posture:
                self._expunge(posture)
            return posture
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving current posture for customer {customer_id}"
            ) from e

    async def save_snapshot(
        self, posture: CustomerRiskPosture,
    ) -> CustomerRiskPosture:
        """
        Save a new posture snapshot, marking previous ones as not current.

        Atomically sets is_current=FALSE on all existing rows for the
        customer, then inserts the new snapshot with is_current=TRUE.

        Args:
            posture: New posture snapshot to save

        Returns:
            Saved posture (detached)
        """
        try:
            await self.session.execute(
                update(CustomerRiskPosture)
                .where(
                    and_(
                        CustomerRiskPosture.customer_id == posture.customer_id,
                        CustomerRiskPosture.is_current == True,
                    )
                )
                .values(is_current=False)
            )

            self.session.add(posture)
            await self.session.commit()
            await self.session.refresh(posture)
            self._expunge(posture)
            return posture
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error saving posture snapshot for customer {posture.customer_id}"
            ) from e

    async def get_history(
        self,
        customer_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CustomerRiskPosture]:
        """
        Get posture history for a customer, most recent first.

        Args:
            customer_id: UUID of the customer
            limit: Maximum number of snapshots to return
            offset: Number of snapshots to skip

        Returns:
            List of detached CustomerRiskPosture snapshots
        """
        try:
            stmt = (
                select(CustomerRiskPosture)
                .where(CustomerRiskPosture.customer_id == customer_id)
                .order_by(desc(CustomerRiskPosture.computed_at))
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            postures = list(result.scalars().all())

            for p in postures:
                self._expunge(p)
            return postures
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving posture history for customer {customer_id}"
            ) from e

    async def count_history(self, customer_id: uuid.UUID) -> int:
        """
        Count total posture snapshots for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            Total snapshot count
        """
        try:
            stmt = (
                select(func.count())
                .select_from(CustomerRiskPosture)
                .where(CustomerRiskPosture.customer_id == customer_id)
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error counting posture history for customer {customer_id}"
            ) from e

    async def get_all_current(self) -> list[CustomerRiskPosture]:
        """
        Get the current posture for every customer that has one.

        Returns:
            List of detached CustomerRiskPosture (one per customer)
        """
        try:
            stmt = (
                select(CustomerRiskPosture)
                .where(CustomerRiskPosture.is_current == True)
                .order_by(desc(CustomerRiskPosture.composite_score))
            )
            result = await self.session.execute(stmt)
            postures = list(result.scalars().all())

            for p in postures:
                self._expunge(p)
            return postures
        except SQLAlchemyError as e:
            raise RuntimeError(
                "Error retrieving all current postures"
            ) from e
