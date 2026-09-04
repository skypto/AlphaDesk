from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.base import Base


class AppUserRecord(Base):
    __tablename__ = "app_users"

    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    auth_subject: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("app_users.user_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    workspace_type: Mapped[str] = mapped_column(String(32), default="CONNECTED_PAPER")
    status: Mapped[str] = mapped_column(String(32), default="ONBOARDING", index=True)
    scanner_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class InvitationRecord(Base):
    __tablename__ = "invitations"

    invitation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    code_format: Mapped[str] = mapped_column(String(32), default="legacy_urlsafe")
    comment: Mapped[str] = mapped_column(String(240), default="")
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class InvitationRedemptionRecord(Base):
    __tablename__ = "invitation_redemptions"
    __table_args__ = (
        UniqueConstraint("invitation_id", "user_id", name="uq_invitation_redemption_user"),
    )

    redemption_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    invitation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("invitations.invitation_id", ondelete="CASCADE")
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="CASCADE")
    )
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkspaceCredentialRecord(Base):
    __tablename__ = "workspace_credentials"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", name="uq_workspace_credential_provider"),
    )

    credential_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), index=True)
    key_version: Mapped[str] = mapped_column(String(32))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    fingerprint: Mapped[str] = mapped_column(String(16))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    validation_status: Mapped[str] = mapped_column(String(32), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DemoSessionRecord(Base):
    __tablename__ = "demo_sessions"

    demo_session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    guardian_halted: Mapped[bool] = mapped_column(Boolean, default=False)
    guardian_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WatchlistSymbolRecord(Base):
    __tablename__ = "watchlist_symbols"
    __table_args__ = (PrimaryKeyConstraint("workspace_id", "symbol", name="pk_watchlist_symbols"),)

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE")
    )
    symbol: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConnectedScanRunRecord(Base):
    __tablename__ = "connected_scan_runs"

    scan_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        index=True,
    )
    trigger: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), default="ALPACA_REAL")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempted_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)


class ConnectedOpportunityRecord(Base):
    __tablename__ = "connected_opportunities"

    opportunity_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        index=True,
    )
    scan_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("connected_scan_runs.scan_run_id", ondelete="SET NULL"),
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(32), default="ALPACA_REAL")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuditRecord(Base):
    __tablename__ = "audit_records"

    audit_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("app_users.user_id", ondelete="SET NULL"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(120), index=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DomainEventRecord(Base):
    __tablename__ = "domain_events"

    event_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    correlation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    causation_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class OutboxEventRecord(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_outbox_event_id"),)

    outbox_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    event_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
    )
    subject: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class BrokerSyncStateRecord(Base):
    __tablename__ = "broker_sync_state"

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(String(32), index=True)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_stream_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stream_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    generation: Mapped[int] = mapped_column(Integer, default=0)
    divergence_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text)


class BrokerAccountRecord(Base):
    __tablename__ = "broker_accounts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "account_number", name="uq_broker_account_workspace_number"
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_number: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    equity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    cash: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    buying_power: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    options_buying_power: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    last_equity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    trading_blocked: Mapped[bool] = mapped_column(Boolean)
    account_blocked: Mapped[bool] = mapped_column(Boolean)
    trade_suspended_by_user: Mapped[bool] = mapped_column(Boolean)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class BrokerPositionRecord(Base):
    __tablename__ = "broker_positions"

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(48), index=True)
    asset_class: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    quantity_available: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    average_entry_price: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    unrealized_pl: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class BrokerOrderRecord(Base):
    __tablename__ = "broker_orders"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "client_order_id", name="uq_broker_order_workspace_client"
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    broker_order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str | None] = mapped_column(String(48), index=True)
    side: Mapped[str | None] = mapped_column(String(16))
    order_type: Mapped[str] = mapped_column(String(32))
    order_class: Mapped[str] = mapped_column(String(32))
    time_in_force: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    filled_average_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class OrderIntentRecord(Base):
    __tablename__ = "order_intents"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "client_order_id", name="uq_order_intent_workspace_client"
        ),
    )

    order_intent_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        index=True,
    )
    client_order_id: Mapped[str] = mapped_column(String(64), index=True)
    risk_decision_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AIWorkflowRunRecord(Base):
    __tablename__ = "ai_workflow_runs"

    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    correlation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(80))
    prompt_versions: Mapped[dict[str, str]] = mapped_column(JSONB)
    schema_version: Mapped[int] = mapped_column(Integer)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    degraded: Mapped[bool] = mapped_column(Boolean, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GuardianIncidentRecord(Base):
    __tablename__ = "guardian_incidents"

    incident_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        index=True,
    )
    state: Mapped[str] = mapped_column(String(32), index=True)
    triggers: Mapped[list[str]] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(Text)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class ResearchObservationRecord(Base):
    __tablename__ = "research_observations"

    observation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    series: Mapped[str] = mapped_column(String(80), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_version: Mapped[str] = mapped_column(String(80))


class StrategyPassportRecord(Base):
    __tablename__ = "strategy_passports"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_strategy_passport_version"),)

    passport_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    data_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
