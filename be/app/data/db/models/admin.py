"""
Admin model — lookup table for traceability of admin actions.

Columns:
- id: UUID (PK)
- name: str

Identity-only for audit trail — no auth, no role management.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db.base import Base


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Relationships ──
    locked_alerts: Mapped[list[Alert]] = relationship(
        back_populates="locked_by_admin",
    )
    feedback_actions: Mapped[list[Feedback]] = relationship(
        back_populates="action_by_admin",
    )
