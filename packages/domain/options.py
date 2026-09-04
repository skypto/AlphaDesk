from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class LegSide(StrEnum):
    LONG = "long"
    SHORT = "short"

    @property
    def sign(self) -> Decimal:
        return Decimal("1") if self is LegSide.LONG else Decimal("-1")


class StructureType(StrEnum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    BULL_CALL_DEBIT_SPREAD = "bull_call_debit_spread"
    BEAR_PUT_DEBIT_SPREAD = "bear_put_debit_spread"
    BULL_PUT_CREDIT_SPREAD = "bull_put_credit_spread"
    BEAR_CALL_CREDIT_SPREAD = "bear_call_credit_spread"
    PROTECTIVE_PUT = "protective_put"
    PROTECTIVE_PUT_SPREAD = "protective_put_spread"


class Greeks(BaseModel):
    model_config = ConfigDict(frozen=True)

    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal


class OptionQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    bid: Decimal = Field(ge=ZERO)
    ask: Decimal = Field(ge=ZERO)
    bid_size: Decimal = Field(ge=ZERO)
    ask_size: Decimal = Field(ge=ZERO)
    quoted_at: datetime
    open_interest: int | None = Field(default=None, ge=0)
    volume: int | None = Field(default=None, ge=0)
    implied_volatility: Decimal | None = Field(default=None, ge=ZERO)
    greeks: Greeks | None = None

    @model_validator(mode="after")
    def validate_market(self) -> OptionQuote:
        if self.quoted_at.tzinfo is None:
            raise ValueError("quoted_at must be timezone-aware")
        if self.ask < self.bid:
            raise ValueError("crossed option quote")
        return self

    @property
    def midpoint(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread_ratio(self) -> Decimal | None:
        midpoint = self.midpoint
        return None if midpoint <= ZERO else (self.ask - self.bid) / midpoint


class OptionContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_id: str
    symbol: str
    underlying_symbol: str
    expiration: date
    strike: Decimal = Field(gt=ZERO)
    option_type: OptionType
    multiplier: int = Field(default=100, gt=0)
    tradable: bool
    quote: OptionQuote


class OptionLeg(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract: OptionContract
    side: LegSide
    ratio: int = Field(default=1, ge=1)
    entry_price: Decimal = Field(ge=ZERO)


class UnderlyingLeg(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    shares: int = Field(gt=0)
    entry_price: Decimal = Field(gt=ZERO)


class OptionStructure(BaseModel):
    model_config = ConfigDict(frozen=True)

    structure_type: StructureType
    quantity: int = Field(default=1, ge=1)
    legs: tuple[OptionLeg, ...]
    underlying: UnderlyingLeg | None = None
    net_premium_per_share: Decimal
    max_loss: Decimal = Field(ge=ZERO)
    max_profit: Decimal | None = Field(default=None, ge=ZERO)
    break_evens: tuple[Decimal, ...]
    greeks: Greeks

    @property
    def is_max_profit_unbounded(self) -> bool:
        return self.max_profit is None


class LiquidityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    supported_underlyings: frozenset[str]
    min_dte: int = Field(ge=0)
    max_dte: int = Field(ge=0)
    max_spread_ratio: Decimal = Field(ge=ZERO)
    min_open_interest: int | None = Field(default=None, ge=0)
    min_quote_size: Decimal = Field(default=Decimal("1"), ge=ZERO)
    max_strike_distance_ratio: Decimal = Field(default=Decimal("0.30"), ge=ZERO)
    max_quote_age_seconds: int = Field(default=30, ge=0)
    require_greeks: bool = True

    @model_validator(mode="after")
    def validate_dte_range(self) -> LiquidityPolicy:
        if self.max_dte < self.min_dte:
            raise ValueError("max_dte must be greater than or equal to min_dte")
        return self


class EligibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool
    reasons: tuple[str, ...] = ()


def utc_now() -> datetime:
    return datetime.now(UTC)
