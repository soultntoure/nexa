"""add_customer_risk_postures

Revision ID: c7f8a9b0d1e2
Revises: f1a2b3c4d5e6
Create Date: 2026-02-12 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7f8a9b0d1e2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'customer_risk_postures',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('posture', sa.String(length=20), nullable=False),
        sa.Column('composite_score', sa.Float(), nullable=False),
        sa.Column('signal_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('signal_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('trigger', sa.String(length=50), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_posture_customer_current',
        'customer_risk_postures',
        ['customer_id'],
        postgresql_where=sa.text('is_current = TRUE'),
    )
    op.create_index(
        'ix_posture_customer_computed',
        'customer_risk_postures',
        ['customer_id', 'computed_at'],
    )
    op.create_index(
        'ix_posture_posture',
        'customer_risk_postures',
        ['posture'],
    )


def downgrade() -> None:
    op.drop_index('ix_posture_posture', table_name='customer_risk_postures')
    op.drop_index('ix_posture_customer_computed', table_name='customer_risk_postures')
    op.drop_index('ix_posture_customer_current', table_name='customer_risk_postures')
    op.drop_table('customer_risk_postures')
