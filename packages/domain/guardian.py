from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class GuardianTrigger(StrEnum):
    MANUAL_KILL_SWITCH = "MANUAL_KILL_SWITCH"
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    STREAM_DISCONNECTED = "STREAM_DISCONNECTED"
    STATE_DIVERGENCE = "STATE_DIVERGENCE"
    DUPLICATE_ORDER_PATTERN = "DUPLICATE_ORDER_PATTERN"
    RISK_POLICY_BREACH = "RISK_POLICY_BREACH"
    REPEATED_ORDER_REJECTIONS = "REPEATED_ORDER_REJECTIONS"
    ABNORMAL_ORDER_RATE = "ABNORMAL_ORDER_RATE"
    UNCOVERED_OPTION_EXPOSURE = "UNCOVERED_OPTION_EXPOSURE"


class GuardianState(StrEnum):
    NORMAL = "NORMAL"
    HALTED = "HALTED"
    RECOVERY_PENDING = "RECOVERY_PENDING"


class GuardianObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: datetime
    latest_market_data_at: datetime | None
    broker_stream_connected: bool
    broker_reconciled: bool
    divergence_count: int = Field(ge=0)
    duplicate_order_patterns: int = Field(ge=0)
    risk_policy_breach: bool
    recent_order_rejections: int = Field(ge=0)
    orders_last_minute: int = Field(ge=0)
    uncovered_short_option_legs: int = Field(ge=0)


class GuardianPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_market_data_age_seconds: int = Field(default=15, ge=1)
    max_recent_order_rejections: int = Field(default=3, ge=1)
    max_orders_per_minute: int = Field(default=5, ge=1)


class GuardianEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    halted: bool
    triggers: tuple[GuardianTrigger, ...]
    pause_new_intents: bool
    cancel_eligible_open_orders: bool
    require_reconciliation: bool


class GuardianIncident(BaseModel):
    model_config = ConfigDict(frozen=True)

    incident_id: UUID = Field(default_factory=uuid4)
    state: GuardianState
    triggers: tuple[GuardianTrigger, ...]
    reason: str
    activated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cleared_at: datetime | None = None


class GuardianStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: GuardianState
    active_incident: GuardianIncident | None = None
    execution_allowed: bool
