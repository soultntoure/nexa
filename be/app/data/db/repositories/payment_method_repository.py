"""
PaymentMethod CRUD operations.

Contains:
- PaymentMethodRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> PaymentMethod | None
  - get_by_customer(customer_id: UUID) -> list[PaymentMethod]
  - get_verified(customer_id: UUID) -> list[PaymentMethod]
  - get_blacklisted() -> list[PaymentMethod]
  - mark_as_used(id: UUID) -> PaymentMethod

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.payment_method import PaymentMethod
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentMethodRepository(BaseRepository[PaymentMethod]):
    """Repository for PaymentMethod entity with verification and risk management."""

    model_class = PaymentMethod

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_customer(self, customer_id: uuid.UUID) -> list[PaymentMethod]:
        """
        Get all payment methods for a customer.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            List of detached PaymentMethods
        """
        try:
            stmt = select(PaymentMethod).where(
                PaymentMethod.customer_id == customer_id
            )
            result = await self.session.execute(stmt)
            payment_methods = list(result.scalars().all())
            
            for pm in payment_methods:
                self._expunge(pm)
            
            return payment_methods
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving payment methods for customer {customer_id}"
            ) from e

    async def get_verified(self, customer_id: uuid.UUID) -> list[PaymentMethod]:
        """
        Get verified payment methods for a customer.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            List of detached verified PaymentMethods
        """
        try:
            stmt = select(PaymentMethod).where(
                PaymentMethod.customer_id == customer_id,
                PaymentMethod.is_verified == True
            )
            result = await self.session.execute(stmt)
            payment_methods = list(result.scalars().all())
            
            for pm in payment_methods:
                self._expunge(pm)
            
            return payment_methods
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving verified payment methods for customer {customer_id}"
            ) from e

    async def get_blacklisted(self) -> list[PaymentMethod]:
        """
        Get all blacklisted payment methods for risk monitoring.
        
        Returns:
            List of detached blacklisted PaymentMethods
        """
        try:
            stmt = select(PaymentMethod).where(
                PaymentMethod.is_blacklisted == True
            )
            result = await self.session.execute(stmt)
            payment_methods = list(result.scalars().all())
            
            for pm in payment_methods:
                self._expunge(pm)
            
            return payment_methods
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving blacklisted payment methods") from e

    async def get_latest_method_risk(self, external_id: str) -> dict[str, Any] | None:
        """Get latest payment method details for fraud indicator scoring."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        pm.is_verified,
                        pm.is_blacklisted,
                        pm.added_at,
                        EXTRACT(EPOCH FROM (NOW() - pm.added_at)) / 86400 AS age_days,
                        (SELECT COUNT(DISTINCT pm2.id)
                         FROM payment_methods pm2
                         WHERE pm2.customer_id = pm.customer_id
                           AND pm2.added_at >= NOW() - INTERVAL '30 days'
                        ) AS methods_added_30d
                    FROM payment_methods pm
                    JOIN customers c ON c.id = pm.customer_id
                    JOIN withdrawals w ON w.payment_method_id = pm.id
                    WHERE c.external_id = :customer_id
                    ORDER BY pm.added_at DESC
                    LIMIT 1
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting payment method risk for customer {external_id}"
            ) from e

    async def mark_as_used(self, id: uuid.UUID) -> PaymentMethod | None:
        """
        Update the last_used_at timestamp for a payment method.

        Args:
            id: UUID of the payment method

        Returns:
            Updated PaymentMethod (detached), None if not found
        """
        try:
            payment_method = await self.session.get(PaymentMethod, id)
            if not payment_method:
                return None

            payment_method.last_used_at = _utcnow()
            await self.session.commit()
            await self.session.refresh(payment_method)
            self._expunge(payment_method)

            return payment_method
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error updating last_used_at for payment method {id}"
            ) from e

    async def find_linked_by_card(
        self, payment_method_id: uuid.UUID, exclude_customer_id: uuid.UUID,
    ) -> list[PaymentMethod]:
        """
        Find all payment methods sharing same last_four + provider.

        Args:
            payment_method_id: Source payment method UUID
            exclude_customer_id: Customer ID to exclude from results

        Returns:
            List of detached PaymentMethods with matching card
        """
        try:
            source_pm = await self.session.get(PaymentMethod, payment_method_id)
            if not source_pm or not source_pm.last_four:
                return []

            stmt = select(PaymentMethod).where(
                PaymentMethod.last_four == source_pm.last_four,
                PaymentMethod.provider == source_pm.provider,
                PaymentMethod.customer_id != exclude_customer_id,
            )
            result = await self.session.execute(stmt)
            payment_methods = list(result.scalars().all())

            for pm in payment_methods:
                self._expunge(pm)

            return payment_methods
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error finding linked cards for payment method {payment_method_id}"
            ) from e
