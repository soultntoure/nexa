"""add_investigation_data_to_evaluations

Revision ID: a1b2c3d4e5f6
Revises: 9c1a887c5cf8
Create Date: 2026-02-10 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9c1a887c5cf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'evaluations' AND column_name = 'investigation_data'"
    ))
    if not result.fetchone():
        op.add_column('evaluations', sa.Column('investigation_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('evaluations', 'investigation_data')
