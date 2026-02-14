"""
Device CRUD operations.

Contains:
- DeviceRepository class (takes AsyncSession)
  - get_by_id(id: UUID) -> Device | None
  - get_by_customer(customer_id: UUID) -> list[Device]
  - get_by_fingerprint(fingerprint: str) -> list[Device]
  - mark_trusted(id: UUID) -> Device
  - update_last_seen(fingerprint: str, customer_id: UUID) -> Device

Rules: async only, expunge before return.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.device import Device
from app.data.db.repositories.base_repository import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeviceRepository(BaseRepository[Device]):
    """Repository for Device entity with fingerprint tracking and trust management."""

    model_class = Device

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_customer(self, customer_id: uuid.UUID) -> list[Device]:
        """
        Get all devices for a customer.
        
        Args:
            customer_id: UUID of the customer
            
        Returns:
            List of detached Devices
        """
        try:
            stmt = select(Device).where(Device.customer_id == customer_id)
            result = await self.session.execute(stmt)
            devices = list(result.scalars().all())
            
            for device in devices:
                self._expunge(device)
            
            return devices
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving devices for customer {customer_id}"
            ) from e

    async def get_by_fingerprint(self, fingerprint: str) -> list[Device]:
        """
        Get all devices with matching fingerprint (cross-account fraud detection).
        
        Args:
            fingerprint: Device fingerprint hash
            
        Returns:
            List of detached Devices across all customers
        """
        try:
            stmt = select(Device).where(Device.fingerprint == fingerprint)
            result = await self.session.execute(stmt)
            devices = list(result.scalars().all())
            
            for device in devices:
                self._expunge(device)
            
            return devices
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving devices by fingerprint {fingerprint}"
            ) from e

    async def get_fingerprint_risk(
        self, external_id: str, fingerprint: str,
    ) -> dict[str, Any] | None:
        """Get device trust, age, and cross-account sharing for fingerprint indicator."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT
                        d.is_trusted,
                        d.first_seen_at,
                        EXTRACT(EPOCH FROM (NOW() - d.first_seen_at)) / 86400 AS device_age_days,
                        (SELECT COUNT(DISTINCT d2.customer_id)
                         FROM devices d2
                         WHERE d2.fingerprint = d.fingerprint
                        ) AS shared_account_count
                    FROM devices d
                    JOIN customers c ON c.id = d.customer_id
                    WHERE c.external_id = :customer_id
                      AND d.fingerprint = :fingerprint
                    LIMIT 1
                """),
                {"customer_id": external_id, "fingerprint": fingerprint},
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error getting fingerprint risk for customer {external_id}"
            ) from e

    async def mark_trusted(self, id: uuid.UUID) -> Device | None:
        """
        Mark a device as trusted.
        
        Args:
            id: UUID of the device
            
        Returns:
            Updated Device (detached), None if not found
        """
        try:
            device = await self.session.get(Device, id)
            if not device:
                return None
            
            device.is_trusted = True
            await self.session.commit()
            await self.session.refresh(device)
            self._expunge(device)
            
            return device
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Error marking device {id} as trusted") from e

    async def update_last_seen(
        self, fingerprint: str, customer_id: uuid.UUID
    ) -> Device | None:
        """
        Update last_seen timestamp for a device.
        
        Args:
            fingerprint: Device fingerprint hash
            customer_id: UUID of the customer
            
        Returns:
            Updated Device (detached), None if not found
        """
        try:
            stmt = select(Device).where(
                Device.fingerprint == fingerprint,
                Device.customer_id == customer_id
            )
            result = await self.session.execute(stmt)
            device = result.scalar_one_or_none()
            
            if not device:
                return None
            
            device.last_seen_at = _utcnow()
            await self.session.commit()
            await self.session.refresh(device)
            self._expunge(device)
            
            return device
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error updating last_seen for device {fingerprint}"
            ) from e
