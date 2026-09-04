from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from packages.broker.alpaca_adapter import AlpacaPaperBrokerAdapter
from packages.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    OrderSubmission,
    SubmissionLeg,
)


def raw_account() -> SimpleNamespace:
    return SimpleNamespace(
        id="account-1",
        account_number="PA123",
        status="ACTIVE",
        currency="USD",
        equity="100000.12",
        cash="45000",
        buying_power="90000",
        options_buying_power="42000",
        last_equity="99500",
        trading_blocked=False,
        account_blocked=False,
        trade_suspended_by_user=False,
    )


def raw_position() -> SimpleNamespace:
    return SimpleNamespace(
        asset_id="asset-1",
        symbol="NVDA260918C00120000",
        asset_class="us_option",
        side="long",
        qty="2",
        qty_available="2",
        avg_entry_price="3.25",
        market_value="700",
        cost_basis="650",
        unrealized_pl="50",
        current_price="3.50",
    )


def raw_order() -> SimpleNamespace:
    now = datetime(2026, 9, 1, 14, tzinfo=UTC)
    return SimpleNamespace(
        id="order-1",
        client_order_id="ad-intent-1",
        status="accepted",
        asset_class="us_option",
        symbol="NVDA260918C00120000",
        side="buy",
        order_type="limit",
        type="limit",
        order_class="simple",
        time_in_force="day",
        qty="2",
        filled_qty="0",
        filled_avg_price=None,
        limit_price="3.30",
        submitted_at=now,
        created_at=now,
        updated_at=now,
        legs=None,
    )


class FakeTradingClient:
    submitted_request: object | None = None

    def get_account(self) -> SimpleNamespace:
        return raw_account()

    def get_all_positions(self) -> list[SimpleNamespace]:
        return [raw_position()]

    def get_orders(self, request: object) -> list[SimpleNamespace]:
        assert request is not None
        return [raw_order()]

    def cancel_order_by_id(self, order_id: str) -> None:
        assert order_id == "order-1"

    def submit_order(self, request: object) -> SimpleNamespace:
        self.submitted_request = request
        return raw_order()

    def close_position(self, symbol_or_asset_id: str) -> SimpleNamespace:
        assert symbol_or_asset_id == "NVDA260918C00120000"
        return raw_order()


class FakeTradingStream:
    def subscribe_trade_updates(self, handler: object) -> None:
        self.handler = handler

    def run(self) -> None:  # pragma: no cover - not used by mapping test
        return None

    def stop(self) -> None:
        return None


@pytest.mark.asyncio
async def test_alpaca_types_are_normalized_at_the_adapter_boundary() -> None:
    adapter = AlpacaPaperBrokerAdapter(
        "paper-key",
        "paper-secret",
        trading_client=FakeTradingClient(),
        trading_stream=FakeTradingStream(),
    )

    snapshot = await adapter.reconcile()

    assert isinstance(snapshot.account, BrokerAccount)
    assert isinstance(snapshot.positions[0], BrokerPosition)
    assert isinstance(snapshot.open_orders[0], BrokerOrder)
    assert snapshot.account.equity.as_tuple().exponent == -2
    assert snapshot.positions[0].asset_class == "us_option"
    assert snapshot.open_orders[0].client_order_id == "ad-intent-1"


@pytest.mark.asyncio
async def test_h3_submission_maps_internal_intent_to_atomic_mleg_request() -> None:
    client = FakeTradingClient()
    adapter = AlpacaPaperBrokerAdapter(
        "paper-key",
        "paper-secret",
        trading_client=client,
        trading_stream=FakeTradingStream(),
    )
    order = await adapter.submit_order(
        OrderSubmission(
            client_order_id="ad-intent-1",
            quantity=1,
            limit_price="3.30",
            legs=(
                SubmissionLeg(symbol="XYZ260925C00100000", side="buy", ratio=1),
                SubmissionLeg(symbol="XYZ260925C00110000", side="sell", ratio=1),
            ),
        )
    )

    assert order.client_order_id == "ad-intent-1"
    assert client.submitted_request is not None
    submitted_request = cast(Any, client.submitted_request)
    assert submitted_request.order_class.value == "mleg"
    assert len(submitted_request.legs) == 2


@pytest.mark.asyncio
async def test_alpaca_close_position_delegates_and_maps_order() -> None:
    client = FakeTradingClient()
    adapter = AlpacaPaperBrokerAdapter(
        "paper-key",
        "paper-secret",
        trading_client=client,
        trading_stream=FakeTradingStream(),
    )
    order = await adapter.close_position("NVDA260918C00120000")
    assert order.broker_order_id == "order-1"
    assert order.status == "accepted"
