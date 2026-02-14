"""add_audit_configs_table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-02-13 04:30:00.000000

Migration:
1. Create audit_configs table for background audit pipeline configuration
"""

from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("max_candidates", sa.Integer(), nullable=False),
        sa.Column("output_dir", sa.String(length=255), nullable=False),
        sa.Column("min_events", sa.Integer(), nullable=False),
        sa.Column("min_accounts", sa.Integer(), nullable=False),
        sa.Column("min_confidence", sa.Float(), nullable=False),
        sa.Column("updated_by", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_configs")
