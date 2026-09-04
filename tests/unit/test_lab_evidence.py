from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from packages.domain.lab import BitemporalObservation, CostModel, HistoricalAnalog
from packages.lab.evidence import (
    SimulationClock,
    compute_fingerprint,
    compute_metrics,
    execution_cost,
    select_historical_analogs,
    walk_forward_windows,
)

NOW = datetime(2026, 9, 1, 14, tzinfo=UTC)


def observation(identifier: int, available_offset: int) -> BitemporalObservation:
    return BitemporalObservation(
        series="news",
        symbol="NVDA",
        observed_at=NOW - timedelta(minutes=10),
        available_at=NOW + timedelta(minutes=available_offset),
        payload={"id": identifier},
        source_version="fixture-v1",
    )


def test_simulation_clock_cannot_see_future_available_data() -> None:
    visible = SimulationClock(NOW).visible((observation(1, -1), observation(2, 1)))
    assert [item.payload["id"] for item in visible] == [1]


def test_data_fingerprint_is_stable_and_sensitive_to_run_metadata() -> None:
    rows = [{"timestamp": NOW.isoformat(), "close": "100.00"}]
    first = compute_fingerprint(
        rows,
        feed="sip",
        adjustment="split",
        timeframe="1Day",
        start=NOW,
        end=NOW + timedelta(days=1),
    )
    second = compute_fingerprint(
        rows,
        feed="sip",
        adjustment="split",
        timeframe="1Day",
        start=NOW,
        end=NOW + timedelta(days=1),
    )
    changed = compute_fingerprint(
        rows,
        feed="iex",
        adjustment="split",
        timeframe="1Day",
        start=NOW,
        end=NOW + timedelta(days=1),
    )
    assert first.sha256 == second.sha256
    assert changed.sha256 != first.sha256


def test_cost_adjusted_metrics_use_sample_sharpe_and_drawdown() -> None:
    cost = execution_cost(
        midpoint=Decimal("2"),
        bid=Decimal("1.90"),
        ask=Decimal("2.10"),
        contracts=2,
        multiplier=100,
        model=CostModel(version="v1", slippage_bps="10", per_contract_fee="0.65"),
    )
    assert cost == Decimal("21.700")
    metrics = compute_metrics(
        initial_equity=Decimal("100000"),
        equity_curve=(Decimal("100000"), Decimal("101000"), Decimal("99000"), Decimal("103000")),
        trade_pnls=(Decimal("1000"), Decimal("-2000"), Decimal("4000")),
        total_costs=cost,
    )
    assert metrics.total_return == Decimal("0.03")
    assert metrics.max_drawdown == Decimal("2000") / Decimal("101000")
    assert metrics.win_rate == Decimal("2") / Decimal("3")
    assert metrics.profit_factor == Decimal("2.5")
    assert metrics.sharpe is not None


def test_walk_forward_windows_never_train_on_test_data() -> None:
    timestamps = tuple(NOW + timedelta(days=index) for index in range(10))
    windows = walk_forward_windows(timestamps, training_size=4, testing_size=2)
    assert len(windows) == 3
    assert all(max(train) < min(test) for train, test in windows)


def test_historical_analogs_are_point_in_time_safe_and_ranked() -> None:
    analogs = (
        HistoricalAnalog(
            event_id="near", available_at=NOW, features={"score": "0.8"}, forward_return="0.1"
        ),
        HistoricalAnalog(
            event_id="far", available_at=NOW, features={"score": "0.1"}, forward_return="-0.2"
        ),
        HistoricalAnalog(
            event_id="future",
            available_at=NOW + timedelta(seconds=1),
            features={"score": "0.81"},
            forward_return="0.5",
        ),
    )
    selected = select_historical_analogs(
        target_features={"score": Decimal("0.82")},
        candidates=analogs,
        clock=SimulationClock(NOW),
    )
    assert [item.event_id for item in selected] == ["near", "far"]
    assert all(item.event_id != "future" for item in selected)


def test_bitemporal_observation_rejects_impossible_availability() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        BitemporalObservation(
            series="news",
            symbol="NVDA",
            observed_at=NOW,
            available_at=NOW - timedelta(seconds=1),
            payload={},
            source_version="fixture-v1",
        )
