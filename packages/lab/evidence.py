from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from itertools import pairwise
from statistics import stdev
from typing import Any

from packages.domain.lab import (
    BitemporalObservation,
    CostModel,
    DataFingerprint,
    HistoricalAnalog,
    PerformanceMetrics,
)


@dataclass(frozen=True)
class SimulationClock:
    now: datetime

    def visible(
        self, observations: tuple[BitemporalObservation, ...]
    ) -> tuple[BitemporalObservation, ...]:
        if self.now.tzinfo is None:
            raise ValueError("simulation clock must be timezone-aware")
        return tuple(
            sorted(
                (item for item in observations if item.available_at <= self.now),
                key=lambda item: (item.observed_at, item.available_at, str(item.observation_id)),
            )
        )


def compute_fingerprint(
    rows: list[dict[str, Any]],
    *,
    feed: str,
    adjustment: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> DataFingerprint:
    canonical = json.dumps(
        {
            "metadata": {
                "feed": feed,
                "adjustment": adjustment,
                "timeframe": timeframe,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "rows": rows,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return DataFingerprint(
        sha256=sha256(canonical.encode()).hexdigest(),
        row_count=len(rows),
        feed=feed,
        adjustment=adjustment,
        timeframe=timeframe,
        start=start,
        end=end,
    )


def execution_cost(
    *,
    midpoint: Decimal,
    bid: Decimal,
    ask: Decimal,
    contracts: int,
    multiplier: int,
    model: CostModel,
) -> Decimal:
    half_spread = max((ask - bid) / Decimal("2"), Decimal("0"))
    slippage = midpoint * model.slippage_bps / Decimal("10000")
    return (half_spread + slippage) * multiplier * contracts + model.per_contract_fee * contracts


def compute_metrics(
    *,
    initial_equity: Decimal,
    equity_curve: tuple[Decimal, ...],
    trade_pnls: tuple[Decimal, ...],
    total_costs: Decimal,
) -> PerformanceMetrics:
    if initial_equity <= 0 or not equity_curve:
        raise ValueError("positive initial equity and non-empty equity curve are required")
    total_return = equity_curve[-1] / initial_equity - 1
    peak = initial_equity
    max_drawdown = Decimal("0")
    daily_returns: list[Decimal] = []
    for previous, current in pairwise(equity_curve):
        peak = max(peak, current)
        max_drawdown = max(max_drawdown, (peak - current) / peak)
        daily_returns.append(current / previous - 1)
    wins = [item for item in trade_pnls if item > 0]
    losses = [item for item in trade_pnls if item < 0]
    win_rate = Decimal(len(wins)) / len(trade_pnls) if trade_pnls else Decimal("0")
    profit_factor = None
    if losses:
        profit_factor = sum(wins, Decimal("0")) / abs(sum(losses, Decimal("0")))
    sharpe = None
    if len(daily_returns) >= 2:
        deviation = stdev(daily_returns)
        if deviation != 0:
            sharpe = (sum(daily_returns, Decimal("0")) / len(daily_returns)) / deviation
    return PerformanceMetrics(
        total_return=total_return,
        max_drawdown=max_drawdown,
        trade_count=len(trade_pnls),
        win_rate=win_rate,
        sharpe=sharpe,
        profit_factor=profit_factor,
        total_costs=total_costs,
    )


def select_historical_analogs(
    *,
    target_features: dict[str, Decimal],
    candidates: tuple[HistoricalAnalog, ...],
    clock: SimulationClock,
    limit: int = 20,
) -> tuple[HistoricalAnalog, ...]:
    if limit < 1:
        raise ValueError("analog limit must be positive")
    ranked: list[HistoricalAnalog] = []
    for candidate in candidates:
        if candidate.available_at > clock.now:
            continue
        if set(candidate.features) != set(target_features):
            continue
        squared = sum(
            (
                (candidate.features[name] - target_features[name])
                * (candidate.features[name] - target_features[name])
                for name in target_features
            ),
            Decimal("0"),
        )
        ranked.append(candidate.model_copy(update={"distance": squared.sqrt()}))
    return tuple(sorted(ranked, key=lambda item: (item.distance, item.event_id))[:limit])


def walk_forward_windows(
    timestamps: tuple[datetime, ...], *, training_size: int, testing_size: int
) -> tuple[tuple[tuple[datetime, ...], tuple[datetime, ...]], ...]:
    if training_size <= 0 or testing_size <= 0:
        raise ValueError("walk-forward window sizes must be positive")
    windows = []
    for start in range(0, len(timestamps) - training_size - testing_size + 1, testing_size):
        train = timestamps[start : start + training_size]
        test = timestamps[start + training_size : start + training_size + testing_size]
        if train and test and max(train) < min(test):
            windows.append((train, test))
    return tuple(windows)
