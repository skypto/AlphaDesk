"""Add disposable Alpaca broker-state projections.

Revision ID: 20260901_0002
Revises: 20260901_0001
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0002"
down_revision: str | None = "20260901_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "broker_sync_state",
        sa.Column("singleton_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stream_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stream_connected", sa.Boolean(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("divergence_count", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("singleton_id"),
    )
    op.create_index("ix_broker_sync_state_state", "broker_sync_state", ["state"])
    op.create_table(
        "broker_accounts",
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("account_number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("equity", sa.Numeric(24, 8), nullable=False),
        sa.Column("cash", sa.Numeric(24, 8), nullable=False),
        sa.Column("buying_power", sa.Numeric(24, 8), nullable=False),
        sa.Column("options_buying_power", sa.Numeric(24, 8), nullable=True),
        sa.Column("last_equity", sa.Numeric(24, 8), nullable=False),
        sa.Column("trading_blocked", sa.Boolean(), nullable=False),
        sa.Column("account_blocked", sa.Boolean(), nullable=False),
        sa.Column("trade_suspended_by_user", sa.Boolean(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("account_id"),
        sa.UniqueConstraint("account_number"),
    )
    op.create_index("ix_broker_accounts_as_of", "broker_accounts", ["as_of"])
    op.create_table(
        "broker_positions",
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=48), nullable=False),
        sa.Column("asset_class", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("quantity_available", sa.Numeric(24, 8), nullable=True),
        sa.Column("average_entry_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(24, 8), nullable=True),
        sa.Column("cost_basis", sa.Numeric(24, 8), nullable=False),
        sa.Column("unrealized_pl", sa.Numeric(24, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("asset_id"),
    )
    op.create_index("ix_broker_positions_symbol", "broker_positions", ["symbol"])
    op.create_index("ix_broker_positions_asset_class", "broker_positions", ["asset_class"])
    op.create_index("ix_broker_positions_as_of", "broker_positions", ["as_of"])
    op.create_table(
        "broker_orders",
        sa.Column("broker_order_id", sa.String(length=64), nullable=False),
        sa.Column("client_order_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("asset_class", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=48), nullable=True),
        sa.Column("side", sa.String(length=16), nullable=True),
        sa.Column("order_type", sa.String(length=32), nullable=False),
        sa.Column("order_class", sa.String(length=32), nullable=False),
        sa.Column("time_in_force", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("filled_average_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("limit_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("broker_order_id"),
        sa.UniqueConstraint("client_order_id"),
    )
    op.create_index("ix_broker_orders_client_order_id", "broker_orders", ["client_order_id"])
    op.create_index("ix_broker_orders_status", "broker_orders", ["status"])
    op.create_index("ix_broker_orders_symbol", "broker_orders", ["symbol"])
    op.create_index("ix_broker_orders_created_at", "broker_orders", ["created_at"])
    op.create_index("ix_broker_orders_updated_at", "broker_orders", ["updated_at"])


def downgrade() -> None:
    op.drop_table("broker_orders")
    op.drop_table("broker_positions")
    op.drop_table("broker_accounts")
    op.drop_table("broker_sync_state")
