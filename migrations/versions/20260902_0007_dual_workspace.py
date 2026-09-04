"""Add isolated demo sessions and connected paper workspaces.

Revision ID: 20260902_0007
Revises: 20260901_0006
Create Date: 2026-09-02

This migration intentionally discards the legacy global broker projection and
Guardian incident. Those records had no tenant owner and must never be exposed
after authenticated workspaces are introduced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0007"
down_revision: str | None = "20260901_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auth_subject", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("auth_subject"),
        sa.UniqueConstraint("email"),
    )
    for column in ("auth_subject", "email", "is_admin", "created_at", "last_seen_at"):
        op.create_index(f"ix_app_users_{column}", "app_users", [column])

    op.create_table(
        "workspaces",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("workspace_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("scanner_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["app_users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id"),
        sa.UniqueConstraint("owner_user_id"),
    )
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])
    op.create_index("ix_workspaces_status", "workspaces", ["status"])
    op.create_index("ix_workspaces_created_at", "workspaces", ["created_at"])
    op.create_index("ix_workspaces_updated_at", "workspaces", ["updated_at"])

    op.create_table(
        "invitations",
        sa.Column("invitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("comment", sa.String(240), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("use_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("invitation_id"),
        sa.UniqueConstraint("token_hash"),
    )
    for column in ("token_hash", "expires_at", "disabled_at", "created_at"):
        op.create_index(f"ix_invitations_{column}", "invitations", [column])

    op.create_table(
        "invitation_redemptions",
        sa.Column("redemption_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invitation_id"], ["invitations.invitation_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("redemption_id"),
        sa.UniqueConstraint("invitation_id", "user_id", name="uq_invitation_redemption_user"),
    )
    op.create_index(
        "ix_invitation_redemptions_redeemed_at", "invitation_redemptions", ["redeemed_at"]
    )

    op.create_table(
        "workspace_credentials",
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("key_version", sa.String(32), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("fingerprint", sa.String(16), nullable=False),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("credential_id"),
        sa.UniqueConstraint("workspace_id", "provider", name="uq_workspace_credential_provider"),
    )
    for column in ("workspace_id", "provider", "validation_status", "enabled", "updated_at"):
        op.create_index(f"ix_workspace_credentials_{column}", "workspace_credentials", [column])

    op.create_table(
        "demo_sessions",
        sa.Column("demo_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("guardian_halted", sa.Boolean(), nullable=False),
        sa.Column("guardian_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("demo_session_id"),
    )
    for column in ("expires_at", "created_at", "updated_at"):
        op.create_index(f"ix_demo_sessions_{column}", "demo_sessions", [column])

    op.create_table(
        "watchlist_symbols",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "symbol", name="pk_watchlist_symbols"),
    )

    op.create_table(
        "connected_opportunities",
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("opportunity_id"),
    )
    for column in ("workspace_id", "symbol", "state", "observed_at", "expires_at", "created_at"):
        op.create_index(f"ix_connected_opportunities_{column}", "connected_opportunities", [column])

    op.create_table(
        "audit_records",
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    for column in ("workspace_id", "actor_user_id", "action", "occurred_at"):
        op.create_index(f"ix_audit_records_{column}", "audit_records", [column])

    # No owner can be established for legacy global state, so discard it.
    for table in (
        "broker_orders",
        "broker_positions",
        "broker_accounts",
        "broker_sync_state",
        "order_intents",
        "guardian_incidents",
    ):
        op.drop_table(table)

    op.create_table(
        "broker_sync_state",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stream_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stream_connected", sa.Boolean(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("divergence_count", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id"),
    )
    op.create_index("ix_broker_sync_state_state", "broker_sync_state", ["state"])

    op.create_table(
        "broker_accounts",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("account_number", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("equity", sa.Numeric(24, 8), nullable=False),
        sa.Column("cash", sa.Numeric(24, 8), nullable=False),
        sa.Column("buying_power", sa.Numeric(24, 8), nullable=False),
        sa.Column("options_buying_power", sa.Numeric(24, 8), nullable=True),
        sa.Column("last_equity", sa.Numeric(24, 8), nullable=False),
        sa.Column("trading_blocked", sa.Boolean(), nullable=False),
        sa.Column("account_blocked", sa.Boolean(), nullable=False),
        sa.Column("trade_suspended_by_user", sa.Boolean(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "account_id"),
        sa.UniqueConstraint(
            "workspace_id", "account_number", name="uq_broker_account_workspace_number"
        ),
    )
    op.create_index("ix_broker_accounts_as_of", "broker_accounts", ["as_of"])

    op.create_table(
        "broker_positions",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(48), nullable=False),
        sa.Column("asset_class", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("quantity_available", sa.Numeric(24, 8), nullable=True),
        sa.Column("average_entry_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(24, 8), nullable=True),
        sa.Column("cost_basis", sa.Numeric(24, 8), nullable=False),
        sa.Column("unrealized_pl", sa.Numeric(24, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "asset_id"),
    )
    for column in ("symbol", "asset_class", "as_of"):
        op.create_index(f"ix_broker_positions_{column}", "broker_positions", [column])

    op.create_table(
        "broker_orders",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_order_id", sa.String(64), nullable=False),
        sa.Column("client_order_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("asset_class", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(48), nullable=True),
        sa.Column("side", sa.String(16), nullable=True),
        sa.Column("order_type", sa.String(32), nullable=False),
        sa.Column("order_class", sa.String(32), nullable=False),
        sa.Column("time_in_force", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("filled_average_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("limit_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "broker_order_id"),
        sa.UniqueConstraint(
            "workspace_id", "client_order_id", name="uq_broker_order_workspace_client"
        ),
    )
    for column in ("client_order_id", "status", "symbol", "created_at", "updated_at"):
        op.create_index(f"ix_broker_orders_{column}", "broker_orders", [column])

    op.create_table(
        "order_intents",
        sa.Column("order_intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_order_id", sa.String(64), nullable=False),
        sa.Column("risk_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("order_intent_id"),
        sa.UniqueConstraint(
            "workspace_id", "client_order_id", name="uq_order_intent_workspace_client"
        ),
    )
    for column in (
        "workspace_id",
        "client_order_id",
        "risk_decision_id",
        "state",
        "created_at",
        "updated_at",
    ):
        op.create_index(f"ix_order_intents_{column}", "order_intents", [column])

    op.create_table(
        "guardian_incidents",
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("triggers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    for column in ("workspace_id", "state", "activated_at", "cleared_at"):
        op.create_index(f"ix_guardian_incidents_{column}", "guardian_incidents", [column])

    op.add_column(
        "domain_events", sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_domain_events_workspace_id", "domain_events", ["workspace_id"])
    op.add_column(
        "outbox_events", sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_outbox_events_workspace_id", "outbox_events", ["workspace_id"])
    op.add_column(
        "ai_workflow_runs", sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_ai_workflow_runs_workspace_id", "ai_workflow_runs", ["workspace_id"])
    op.add_column(
        "research_observations",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_research_observations_workspace_id", "research_observations", ["workspace_id"]
    )


def downgrade() -> None:
    raise RuntimeError(
        "The dual-workspace security migration is intentionally irreversible because legacy "
        "global broker data has no safe tenant owner. Restore a pre-migration backup instead."
    )
