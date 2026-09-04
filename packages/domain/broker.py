from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.system import BrokerState


class OrderStatus(StrEnum):
    NEW = "new"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"
    REPLACED = "replaced"
    UNKNOWN = "unknown"


class BrokerAccount(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    account_number: str
    status: str
    currency: str
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    options_buying_power: Decimal | None = None
    last_equity: Decimal
    trading_blocked: bool
    account_blocked: bool
    trade_suspended_by_user: bool
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BrokerPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: str
    symbol: str
    asset_class: str
    side: str
    quantity: Decimal
    quantity_available: Decimal | None = None
    average_entry_price: Decimal
    market_value: Decimal | None = None
    cost_basis: Decimal
    unrealized_pl: Decimal
    current_price: Decimal | None = None
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BrokerOrderLeg(BaseModel):
    model_config = ConfigDict(frozen=True)

    broker_order_id: str
    symbol: str
    side: str
    quantity: Decimal | None = None
    filled_quantity: Decimal
    status: str


class BrokerOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    broker_order_id: str
    client_order_id: str
    status: str
    asset_class: str
    symbol: str | None = None
    side: str | None = None
    order_type: str
    order_class: str
    time_in_force: str
    quantity: Decimal | None = None
    filled_quantity: Decimal
    filled_average_price: Decimal | None = None
    limit_price: Decimal | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    legs: tuple[BrokerOrderLeg, ...] = ()


class BrokerTradeUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: str
    order: BrokerOrder
    execution_id: str | None = None
    price: Decimal | None = None
    quantity: Decimal | None = None
    position_quantity: Decimal | None = None
    occurred_at: datetime


class ReconciliationSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    account: BrokerAccount
    positions: tuple[BrokerPosition, ...]
    open_orders: tuple[BrokerOrder, ...]
    reconciled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BrokerSyncStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: BrokerState
    last_reconciled_at: datetime | None = None
    last_stream_event_at: datetime | None = None
    stream_connected: bool = False
    generation: int = 0
    divergence_count: int = 0
    failure_reason: str | None = None


class SubmissionLeg(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    side: Literal["buy", "sell"]
    ratio: int = Field(ge=1)


class OrderSubmission(BaseModel):
    """Internal multi-leg submission DTO. Alpaca types never cross this boundary."""

    model_config = ConfigDict(frozen=True)

    client_order_id: str
    quantity: int = Field(ge=1)
    limit_price: Decimal
    time_in_force: Literal["day"] = "day"
    legs: tuple[SubmissionLeg, ...]
