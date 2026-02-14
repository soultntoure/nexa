"""Seed admin identities for traceability demos."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.models.admin import Admin

# Deterministic UUIDs for consistent demos
ADMIN_RISHI_ID = uuid.UUID("36c12770-a379-48b4-b400-f053a9fb1b35")
ADMIN_AISHA_ID = uuid.UUID("489921e9-8e28-4b15-8f0e-e2282ea7b4a8")


async def _seed_admins(session: AsyncSession) -> None:
    """Seed two demo admins."""
    session.add(Admin(id=ADMIN_RISHI_ID, name="Rishi Mohan"))
    session.add(Admin(id=ADMIN_AISHA_ID, name="Aisha Patel"))
