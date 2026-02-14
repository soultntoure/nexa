"""rename_fraud_patterns_add_phase2_tables

Revision ID: d1e2f3a4b5c6
Revises: c7f8a9b0d1e2
Create Date: 2026-02-12 18:00:00.000000

Migration:
1. Rename fraud_patterns → customer_fraud_signals (existing Phase 1 table)
2. Rename index ix_fp_customer_signal → ix_cfs_customer_signal
3. Create new fraud_patterns table (Phase 2 cross-customer patterns)
4. Create new pattern_matches table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c7f8a9b0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename existing fraud_patterns table → customer_fraud_signals
    op.rename_table('fraud_patterns', 'customer_fraud_signals')

    # 2. Rename the existing index
    op.execute('ALTER INDEX ix_fp_customer_signal RENAME TO ix_cfs_customer_signal')

    # 3. Create new Phase 2 fraud_patterns table
    op.create_table(
        'fraud_patterns',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='candidate'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('frequency', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('precision_score', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_by', sa.Uuid(), nullable=True),
        sa.Column('disabled_by', sa.Uuid(), nullable=True),
        sa.Column('disabled_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_patterns_state', 'fraud_patterns', ['state'])
    op.create_index('ix_patterns_type_state', 'fraud_patterns', ['pattern_type', 'state'])

    # 4. Create pattern_matches table
    op.create_table(
        'pattern_matches',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('pattern_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.ForeignKeyConstraint(['pattern_id'], ['fraud_patterns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_pm_customer_current', 'pattern_matches', ['customer_id'],
        postgresql_where=sa.text('is_current = TRUE'),
    )
    op.create_index(
        'ix_pm_pattern_current', 'pattern_matches', ['pattern_id'],
        postgresql_where=sa.text('is_current = TRUE'),
    )
    op.create_index(
        'ix_pm_unique_current', 'pattern_matches', ['pattern_id', 'customer_id'],
        unique=True, postgresql_where=sa.text('is_current = TRUE'),
    )


def downgrade() -> None:
    # Drop pattern_matches
    op.drop_index('ix_pm_unique_current', table_name='pattern_matches')
    op.drop_index('ix_pm_pattern_current', table_name='pattern_matches')
    op.drop_index('ix_pm_customer_current', table_name='pattern_matches')
    op.drop_table('pattern_matches')

    # Drop new fraud_patterns
    op.drop_index('ix_patterns_type_state', table_name='fraud_patterns')
    op.drop_index('ix_patterns_state', table_name='fraud_patterns')
    op.drop_table('fraud_patterns')

    # Restore index name
    op.execute('ALTER INDEX ix_cfs_customer_signal RENAME TO ix_fp_customer_signal')

    # Rename back to fraud_patterns
    op.rename_table('customer_fraud_signals', 'fraud_patterns')
