"""
Admin CRUD operations.

Contains:
- AdminRepository class (takes AsyncSession)
  - get_by_name(name: str) -> Admin | None
  - list_active() -> list[Admin]

Rules: async only, expunge before return.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.models.admin import Admin
from app.data.db.repositories.base_repository import BaseRepository


class AdminRepository(BaseRepository[Admin]):
    """Repository for Admin entity."""

    model_class = Admin

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_name(self, name: str) -> Admin | None:
        """
        Retrieve an admin by name.

        Args:
            name: Admin name to look up

        Returns:
            Detached Admin if found, None otherwise
        """
        try:
            stmt = select(Admin).where(Admin.name == name)
            result = await self.session.execute(stmt)
            admin = result.scalar_one_or_none()
            if admin:
                self._expunge(admin)
            return admin
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving Admin by name {name}"
            ) from e

    async def list_active(self) -> list[Admin]:
        """
        List all admins (no is_active filter since model is simplified).

        Returns:
            List of detached Admins
        """
        try:
            stmt = select(Admin).order_by(Admin.name)
            result = await self.session.execute(stmt)
            admins = list(result.scalars().all())
            for admin in admins:
                self._expunge(admin)
            return admins
        except SQLAlchemyError as e:
            raise RuntimeError("Error listing admins") from e
