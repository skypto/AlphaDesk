"""Add tenant-scoped connected scan runs.

Revision ID: 20260903_0009
Revises: 20260902_0008
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260903_0009"
down_revision: str | None = "20260902_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connected_scan_runs",
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempted_count", sa.Integer(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("scan_run_id"),
    )
    op.create_index(
        "ix_connected_scan_runs_workspace_id",
        "connected_scan_runs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_connected_scan_runs_started_at", "connected_scan_runs", ["started_at"]
    )
    op.create_index(
        "ix_connected_scan_runs_completed_at", "connected_scan_runs", ["completed_at"]
    )
    op.add_column(
        "connected_opportunities",
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_connected_opportunities_scan_run_id",
        "connected_opportunities",
        "connected_scan_runs",
        ["scan_run_id"],
        ["scan_run_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_connected_opportunities_scan_run_id",
        "connected_opportunities",
        ["scan_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_connected_opportunities_scan_run_id", table_name="connected_opportunities"
    )
    op.drop_constraint(
        "fk_connected_opportunities_scan_run_id",
        "connected_opportunities",
        type_="foreignkey",
    )
    op.drop_column("connected_opportunities", "scan_run_id")
    op.drop_table("connected_scan_runs")
