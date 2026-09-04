"""Add versioned AI workflow audit storage.

Revision ID: 20260901_0004
Revises: 20260901_0003
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0004"
down_revision: str | None = "20260901_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_workflow_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("prompt_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_ai_workflow_runs_correlation_id", "ai_workflow_runs", ["correlation_id"])
    op.create_index("ix_ai_workflow_runs_degraded", "ai_workflow_runs", ["degraded"])
    op.create_index("ix_ai_workflow_runs_created_at", "ai_workflow_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_workflow_runs")
