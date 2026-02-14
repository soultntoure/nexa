"""
Admin endpoints — minimal CRUD for admin identity lookup.

GET  /api/admins  — List all admins (for UI dropdown)
POST /api/admins  — Create a new admin (name only)
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db.engine import get_session
from app.data.db.models.admin import Admin
from app.data.db.repositories.admin_repository import AdminRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admins", tags=["admins"])


class CreateAdminRequest(BaseModel):
    name: str


@router.get("")
async def list_admins(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List all admins for UI dropdown."""
    try:
        repo = AdminRepository(session)
        admins = await repo.list_active()
        return {
            "admins": [
                {"id": str(a.id), "name": a.name}
                for a in admins
            ],
        }
    except Exception as exc:
        logger.exception("list_admins error: %s", exc)
        return {"admins": []}


@router.post("")
async def create_admin(
    request: CreateAdminRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Create a new admin entry."""
    try:
        repo = AdminRepository(session)
        admin = Admin(name=request.name)
        created = await repo.create(admin)
        return {"id": str(created.id), "name": created.name}
    except Exception as exc:
        logger.exception("create_admin error: %s", exc)
        return {"error": str(exc)}
