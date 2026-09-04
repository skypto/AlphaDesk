"""Add bitemporal research observations and Strategy Passports.

Revision ID: 20260901_0006
Revises: 20260901_0005
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0006"
down_revision: str | None = "20260901_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_observations",
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("series", sa.String(length=80), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_version", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    for column in ("series", "symbol", "observed_at", "available_at"):
        op.create_index(f"ix_research_observations_{column}", "research_observations", [column])
    op.create_table(
        "strategy_passports",
        sa.Column("passport_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("passport_id"),
        sa.UniqueConstraint("name", "version", name="uq_strategy_passport_version"),
    )
    op.create_index("ix_strategy_passports_name", "strategy_passports", ["name"])
    op.create_index(
        "ix_strategy_passports_data_fingerprint", "strategy_passports", ["data_fingerprint"]
    )
    op.create_index("ix_strategy_passports_created_at", "strategy_passports", ["created_at"])


def downgrade() -> None:
    op.drop_table("strategy_passports")
    op.drop_table("research_observations")
