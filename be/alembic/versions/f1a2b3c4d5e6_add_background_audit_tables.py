"""Add background audit tables.

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f1a2b3c4d5e6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("run_mode", sa.String(20), nullable=False, server_default="full"),
        sa.Column("config_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("counters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("timings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_runs_run_id", "audit_runs", ["run_id"], unique=True)
    op.create_index("ix_audit_runs_idempotency", "audit_runs", ["idempotency_key"], unique=True)
    op.create_index("ix_audit_runs_status", "audit_runs", ["status"])

    op.create_table(
        "audit_text_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.String(128), nullable=False, unique=True),
        sa.Column("evaluation_id", sa.Uuid(), sa.ForeignKey("evaluations.id"), nullable=False),
        sa.Column("withdrawal_id", sa.Uuid(), sa.ForeignKey("withdrawals.id"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_name", sa.String(64), nullable=False),
        sa.Column("text_masked", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("decision_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("embedding_model_name", sa.String(64), nullable=True),
        sa.Column("vector_status", sa.String(20), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_text_units_unit_id", "audit_text_units", ["unit_id"], unique=True)
    op.create_index("ix_audit_text_units_text_hash", "audit_text_units", ["text_hash"])
    op.create_index("ix_audit_text_units_evaluation_id", "audit_text_units", ["evaluation_id"])

    op.create_table(
        "audit_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.String(128), nullable=False, unique=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("cluster_id", sa.String(64), nullable=True),
        sa.Column("cluster_fingerprint", sa.String(64), nullable=True),
        sa.Column("novelty_status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("matched_cluster_id", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("support_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("support_accounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pattern_card", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ignore_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suppressed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_candidates_candidate_id", "audit_candidates", ["candidate_id"], unique=True)
    op.create_index("ix_audit_candidates_run_id", "audit_candidates", ["run_id"])
    op.create_index("ix_audit_candidates_status", "audit_candidates", ["status"])

    op.create_table(
        "audit_candidate_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.String(128), sa.ForeignKey("audit_candidates.candidate_id"), nullable=False),
        sa.Column("unit_id", sa.String(128), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False, server_default="supporting"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_evidence_candidate_id", "audit_candidate_evidence", ["candidate_id"])
    op.create_index("ix_audit_evidence_unit_id", "audit_candidate_evidence", ["unit_id"])


def downgrade() -> None:
    op.drop_table("audit_candidate_evidence")
    op.drop_table("audit_candidates")
    op.drop_table("audit_text_units")
    op.drop_table("audit_runs")
