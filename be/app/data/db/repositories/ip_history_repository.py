"""
IPHistory CRUD operations.

Contains:
- IPHistoryRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> IPHistory | None
  - get_by_customer(customer_id: UUID, limit: int) -> list[IPHistory]
  - get_by_ip(ip_address: str) -> list[IPHistory]
  - get_vpn_ips(customer_id: UUID) -> list[IPHistory]
  - update_last_seen(ip_address: str, customer_id: UUID) -> IPHistory

Rules: async only, use indexes, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from typing import Any

from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.ip_history import IPHistory
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IPHistoryRepository(BaseRepository[IPHistory]):
    """Repository for IPHistory entity with VPN detection and geographic analysis."""

    model_class = IPHistory

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_customer(
        self, customer_id: uuid.UUID, limit: int = 50
    ) -> list[IPHistory]:
        """
        Get IP history for a customer, ordered by last seen (most recent first).
        
        Args:
            customer_id: UUID of the customer
            limit: Maximum number of records to return
            
        Returns:
            List of detached IPHistory records
        """
        try:
            stmt = (
                select(IPHistory)
                .where(IPHistory.customer_id == customer_id)
                .order_by(desc(IPHistory.last_seen_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            history = list(result.scalars().all())
            
            for record in history:
                self._expunge(record)
            
            return history
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving IP history for customer {customer_id}"
            ) from e

    async def get_by_ip(self, ip_address: str) -> list[IPHistory]:
        """
        Get all customers who used a specific IP (fraud detection).
        
        Args:
            ip_address: IP address to search for
            
        Returns:
            List of detached IPHistory records across all customers
        """
        try:
            stmt = select(IPHistory).where(IPHistory.ip_address == ip_address)
            result = await self.session.execute(stmt)
            history = list(result.scalars().all())
            
            for record in history:
                self._expunge(record)
            
            return history
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving IP history for IP {ip_address}"
            ) from e

    async def get_vpn_ips(self, customer_id: uuid.UUID) -> list[IPHistory]:
        """
        Get VPN IP addresses used by a customer.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            List of detached IPHistory records where is_vpn=True
        """
        try:
            stmt = select(IPHistory).where(
                IPHistory.customer_id == customer_id,
                IPHistory.is_vpn == True
            )
            result = await self.session.execute(stmt)
            history = list(result.scalars().all())
            
            for record in history:
                self._expunge(record)
            
            return history
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving VPN IPs for customer {customer_id}"
            ) from e

    async def get_recent_with_country(
        self, external_id: str, limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent IP history with home country for geographic indicator."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        ih.ip_address,
                        ih.location,
                        ih.is_vpn,
                        ih.last_seen_at,
                        c.country AS home_country
                    FROM ip_history ih
                    JOIN customers c ON c.id = ih.customer_id
                    WHERE c.external_id = :customer_id
                    ORDER BY ih.last_seen_at DESC
                    LIMIT :lim
                """),
                {"customer_id": external_id, "lim": limit},
            )
            return [dict(row) for row in result.mappings().all()]
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting IP history for customer {external_id}"
            ) from e

    async def get_distinct_countries_7d(self, external_id: str) -> int:
        """Count distinct countries in the last 7 days."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT COUNT(DISTINCT
                        SPLIT_PART(ih.location, ', ', 2)
                    ) AS distinct_countries
                    FROM ip_history ih
                    JOIN customers c ON c.id = ih.customer_id
                    WHERE c.external_id = :customer_id
                      AND ih.last_seen_at >= NOW() - INTERVAL '7 days'
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return int(row["distinct_countries"]) if row else 0
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting distinct countries for customer {external_id}"
            ) from e

    async def get_distinct_countries_all_time(self, external_id: str) -> int:
        """Count distinct countries across all IP history for a customer."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT COUNT(DISTINCT
                        SPLIT_PART(ih.location, ', ', 2)
                    ) AS distinct_countries
                    FROM ip_history ih
                    JOIN customers c ON c.id = ih.customer_id
                    WHERE c.external_id = :customer_id
                """),
                {"customer_id": external_id},
            )
            row = result.mappings().first()
            return int(row["distinct_countries"]) if row else 0
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting all-time countries for {external_id}"
            ) from e

    async def update_last_seen(
        self, ip_address: str, customer_id: uuid.UUID
    ) -> IPHistory | None:
        """
        Update last_seen timestamp for an IP-customer combination.
        
        Args:
            ip_address: IP address
            customer_id: UUID of the customer
            
        Returns:
            Updated IPHistory (detached), None if not found
        """
        try:
            stmt = select(IPHistory).where(
                IPHistory.ip_address == ip_address,
                IPHistory.customer_id == customer_id
            )
            result = await self.session.execute(stmt)
            record = result.scalar_one_or_none()
            
            if not record:
                return None
            
            record.last_seen_at = _utcnow()
            await self.session.commit()
            await self.session.refresh(record)
            self._expunge(record)
            
            return record
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error updating last_seen for IP {ip_address}"
            ) from e
