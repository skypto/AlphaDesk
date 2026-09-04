"""Add immutable order intents and atomic idempotency state.

Revision ID: 20260901_0003
Revises: 20260901_0002
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0003"
down_revision: str | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "order_intents",
        sa.Column("order_intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_order_id", sa.String(length=64), nullable=False),
        sa.Column("risk_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("order_intent_id"),
        sa.UniqueConstraint("client_order_id"),
    )
    op.create_index("ix_order_intents_client_order_id", "order_intents", ["client_order_id"])
    op.create_index("ix_order_intents_risk_decision_id", "order_intents", ["risk_decision_id"])
    op.create_index("ix_order_intents_state", "order_intents", ["state"])
    op.create_index("ix_order_intents_created_at", "order_intents", ["created_at"])
    op.create_index("ix_order_intents_updated_at", "order_intents", ["updated_at"])


def downgrade() -> None:
    op.drop_table("order_intents")
