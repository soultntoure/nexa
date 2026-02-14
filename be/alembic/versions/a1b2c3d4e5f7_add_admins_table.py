"""Add admins table and lockdown traceability columns.

Revision ID: a1b2c3d4e5f7
Revises: e2f3a4b5c6d7
Create Date: 2026-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f7"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
    )

    op.add_column(
        "alerts",
        sa.Column(
            "locked_by_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admins.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "alerts",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "feedback",
        sa.Column(
            "action_by_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admins.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("feedback", "action_by_admin_id")
    op.drop_column("alerts", "locked_at")
    op.drop_column("alerts", "locked_by_admin_id")
    op.drop_table("admins")
