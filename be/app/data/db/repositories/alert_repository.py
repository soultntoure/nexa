"""
Alert CRUD operations.

Contains:
- AlertRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> Alert | None
  - get_recent(limit: int, include_read: bool) -> list[Alert]
  - get_by_customer(customer_id: UUID, limit: int) -> list[Alert]
  - get_unread() -> list[Alert]
  - mark_as_read(id: UUID) -> Alert

Rules: async only, use indexes, expunge before return.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.alert import Alert
from app.data.db.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """Repository for Alert entity with read status management and filtering."""

    model_class = Alert

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_recent(
        self, limit: int = 50, include_read: bool = False
    ) -> list[Alert]:
        """
        Get recent alerts, optionally filtered by read status.
        
        Args:
            limit: Maximum number of alerts to return
            include_read: If False, only return unread alerts
            
        Returns:
            List of detached Alerts, most recent first
        """
        try:
            stmt = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
            
            if not include_read:
                stmt = stmt.where(Alert.is_read == False)
            
            result = await self.session.execute(stmt)
            alerts = list(result.scalars().all())
            
            for alert in alerts:
                self._expunge(alert)
            
            return alerts
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving recent alerts") from e

    async def get_by_customer(
        self, customer_id: uuid.UUID, limit: int = 20
    ) -> list[Alert]:
        """
        Get alerts for a specific customer.
        
        Args:
            customer_id: UUID of the customer
            limit: Maximum number of alerts to return
            
        Returns:
            List of detached Alerts, most recent first
        """
        try:
            stmt = (
                select(Alert)
                .where(Alert.customer_id == customer_id)
                .order_by(desc(Alert.created_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            alerts = list(result.scalars().all())
            
            for alert in alerts:
                self._expunge(alert)
            
            return alerts
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving alerts for customer {customer_id}"
            ) from e

    async def get_unread(self) -> list[Alert]:
        """
        Get all unread alerts for dashboard display.
        
        Returns:
            List of detached unread Alerts, most recent first
        """
        try:
            stmt = (
                select(Alert)
                .where(Alert.is_read == False)
                .order_by(desc(Alert.created_at))
            )
            result = await self.session.execute(stmt)
            alerts = list(result.scalars().all())
            
            for alert in alerts:
                self._expunge(alert)
            
            return alerts
        except SQLAlchemyError as e:
            raise RuntimeError("Error retrieving unread alerts") from e

    async def mark_as_read(self, id: uuid.UUID) -> Alert | None:
        """
        Mark an alert as read.
        
        Args:
            id: UUID of the alert
            
        Returns:
            Updated Alert (detached), None if not found
        """
        try:
            alert = await self.session.get(Alert, id)
            if not alert:
                return None
            
            alert.is_read = True
            await self.session.commit()
            await self.session.refresh(alert)
            self._expunge(alert)
            
            return alert
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Error marking alert {id} as read") from e
