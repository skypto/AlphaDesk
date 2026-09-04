"""Add immutable Guardian incidents.

Revision ID: 20260901_0005
Revises: 20260901_0004
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0005"
down_revision: str | None = "20260901_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guardian_incidents",
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("triggers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    op.create_index("ix_guardian_incidents_state", "guardian_incidents", ["state"])
    op.create_index("ix_guardian_incidents_activated_at", "guardian_incidents", ["activated_at"])
    op.create_index("ix_guardian_incidents_cleared_at", "guardian_incidents", ["cleared_at"])


def downgrade() -> None:
    op.drop_table("guardian_incidents")
