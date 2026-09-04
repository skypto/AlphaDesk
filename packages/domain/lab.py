from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BitemporalObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: UUID = Field(default_factory=uuid4)
    series: str
    symbol: str
    observed_at: datetime
    available_at: datetime
    payload: dict[str, Any]
    source_version: str

    @model_validator(mode="after")
    def validate_times(self) -> BitemporalObservation:
        if self.observed_at.tzinfo is None or self.available_at.tzinfo is None:
            raise ValueError("bitemporal timestamps must be timezone-aware")
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        return self


class DataFingerprint(BaseModel):
    model_config = ConfigDict(frozen=True)

    sha256: str
    row_count: int = Field(ge=0)
    feed: str
    adjustment: str
    timeframe: str
    start: datetime
    end: datetime


class CostModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    slippage_bps: Decimal = Field(ge=0)
    per_contract_fee: Decimal = Field(ge=0)


class PerformanceMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_return: Decimal
    max_drawdown: Decimal
    trade_count: int
    win_rate: Decimal
    sharpe: Decimal | None
    profit_factor: Decimal | None
    total_costs: Decimal


class HistoricalAnalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    available_at: datetime
    features: dict[str, Decimal]
    forward_return: Decimal
    distance: Decimal | None = None


class StrategyPassport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passport_id: UUID = Field(default_factory=uuid4)
    name: str
    version: str
    owner: str
    hypothesis: str
    asset_universe: tuple[str, ...]
    entry_logic: str
    exit_logic: str
    dte_strike_policy: str
    risk_assumptions: tuple[str, ...]
    latency_budget_seconds: int = Field(gt=0)
    historical_test_ranges: tuple[str, ...]
    out_of_sample_results: dict[str, Decimal]
    walk_forward_results: dict[str, Decimal]
    slippage_assumptions: str
    known_failure_regimes: tuple[str, ...]
    paper_status: str
    approved_risk_limits: dict[str, Decimal]
    data_fingerprint: DataFingerprint
