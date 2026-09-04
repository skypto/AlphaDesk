from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.domain.options import OptionStructure


class Direction(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class CatalystFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)

    catalyst_confidence: Decimal = Field(ge=0, le=1)
    sentiment: Decimal = Field(ge=-1, le=1)
    relative_volume: Decimal = Field(ge=0)
    price_momentum: Decimal = Field(ge=-1, le=1)
    gap_percent: Decimal
    market_confirmation: Decimal = Field(ge=-1, le=1)
    sector_confirmation: Decimal = Field(ge=-1, le=1)
    liquidity_score: Decimal = Field(ge=0, le=1)


class Signal(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: UUID = Field(default_factory=uuid4)
    symbol: str
    strategy_family: Literal["CATALYST_MOMENTUM"] = "CATALYST_MOMENTUM"
    observed_at: datetime
    features: CatalystFeatures
    score: Decimal = Field(ge=0, le=100)
    source_versions: dict[str, str]


class TradeIdea(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_idea_id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    symbol: str
    direction: Direction
    thesis: str
    holding_horizon: timedelta
    entry_window: timedelta
    exit_logic: str
    confidence: Decimal = Field(ge=0, le=1)


class NoTrade(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: UUID
    reason_codes: tuple[str, ...]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RankedCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    structure_id: UUID = Field(default_factory=uuid4)
    trade_idea_id: UUID
    structure: OptionStructure
    rank_score: Decimal
    rank_components: dict[str, Decimal]


class RiskCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    detail: str


class RiskDecisionValue(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class RiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    risk_decision_id: UUID = Field(default_factory=uuid4)
    structure_id: UUID
    decision: RiskDecisionValue
    checks: tuple[RiskCheck, ...]
    risk_budget_used: Decimal = Field(ge=0)
    calculated_max_loss: Decimal = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntentLeg(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    side: Literal["buy", "sell"]
    ratio: int = Field(ge=1)


class OrderIntent(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_intent_id: UUID
    client_order_id: str
    risk_decision_id: UUID
    legs: tuple[IntentLeg, ...]
    quantity: int = Field(ge=1)
    limit_price: Decimal
    time_in_force: Literal["day"] = "day"
    execution_policy: str
    created_at: datetime

    @model_validator(mode="after")
    def validate_identifier(self) -> OrderIntent:
        expected = stable_client_order_id(
            self.risk_decision_id,
            self.legs,
            self.quantity,
            self.limit_price,
            self.time_in_force,
            self.execution_policy,
        )
        if self.client_order_id != expected:
            raise ValueError("client_order_id does not match immutable intent identity")
        return self


def stable_client_order_id(
    risk_decision_id: UUID,
    legs: tuple[IntentLeg, ...],
    quantity: int,
    limit_price: Decimal,
    time_in_force: str,
    execution_policy: str,
) -> str:
    canonical_legs = ",".join(f"{leg.symbol}:{leg.side}:{leg.ratio}" for leg in legs)
    canonical = "|".join(
        (
            str(risk_decision_id),
            canonical_legs,
            str(quantity),
            str(limit_price.normalize()),
            time_in_force,
            execution_policy,
        )
    )
    return f"ad-{sha256(canonical.encode()).hexdigest()[:32]}"
