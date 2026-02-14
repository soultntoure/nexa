"""
Customer CRUD operations.

Contains:
- CustomerRepository class (takes AsyncSession)
  - get_by_id(customer_id: UUID) -> Customer | None
  - get_by_external_id(external_id: str) -> Customer | None
  - get_with_devices(customer_id: UUID) -> Customer (eager load devices)
  - get_with_payment_methods(customer_id: UUID) -> Customer
  - list_flagged() -> list[Customer] (benchmark utility)

Rules: async only, use selectinload for relationships, expunge before return.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.customer import Customer
from app.data.db.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer entity with domain-specific query methods."""

    model_class = Customer

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_external_id(self, external_id: str) -> Customer | None:
        """
        Retrieve customer by their external ID.
        
        Args:
            external_id: External customer identifier
            
        Returns:
            Detached Customer if found, None otherwise
        """
        try:
            stmt = select(Customer).where(Customer.external_id == external_id)
            result = await self.session.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                self._expunge(customer)
            return customer
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving customer by external_id {external_id}"
            ) from e

    async def get_with_devices(self, customer_id: uuid.UUID) -> Customer | None:
        """
        Retrieve customer with all associated devices eager loaded.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            Detached Customer with devices loaded, None if not found
        """
        try:
            stmt = (
                select(Customer)
                .where(Customer.id == customer_id)
                .options(selectinload(Customer.devices))
            )
            result = await self.session.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                self._expunge(customer)
            return customer
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving customer {customer_id} with devices"
            ) from e

    async def get_with_payment_methods(
        self, customer_id: uuid.UUID
    ) -> Customer | None:
        """
        Retrieve customer with all payment methods eager loaded.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            Detached Customer with payment methods loaded, None if not found
        """
        try:
            stmt = (
                select(Customer)
                .where(Customer.id == customer_id)
                .options(selectinload(Customer.payment_methods))
            )
            result = await self.session.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                self._expunge(customer)
            return customer
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving customer {customer_id} with payment methods"
            ) from e

    async def list_flagged(self) -> list[Customer]:
        """
        List all flagged customers (for benchmark/testing utility).
        
        Returns:
            List of detached Customer entities where is_flagged=True
        """
        try:
            stmt = select(Customer).where(Customer.is_flagged == True)
            result = await self.session.execute(stmt)
            customers = list(result.scalars().all())
            
            for customer in customers:
                self._expunge(customer)
            
            return customers
        except SQLAlchemyError as e:
            raise RuntimeError("Error listing flagged customers") from e
