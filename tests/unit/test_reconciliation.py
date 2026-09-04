from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from packages.broker.projections import MemoryBrokerProjectionStore
from packages.broker.reconciliation import BrokerExecutionGate, ReconciliationService
from packages.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    ReconciliationSnapshot,
)
from packages.domain.system import BrokerState

NOW = datetime(2026, 9, 1, 14, tzinfo=UTC)


def account(*, blocked: bool = False) -> BrokerAccount:
    return BrokerAccount(
        account_id="account-1",
        account_number="PA123",
        status="ACTIVE",
        currency="USD",
        equity=Decimal("100000"),
        cash=Decimal("50000"),
        buying_power=Decimal("100000"),
        options_buying_power=Decimal("50000"),
        last_equity=Decimal("100000"),
        trading_blocked=blocked,
        account_blocked=False,
        trade_suspended_by_user=False,
        as_of=NOW,
    )


def position(asset_id: str) -> BrokerPosition:
    return BrokerPosition(
        asset_id=asset_id,
        symbol="NVDA260918C00120000",
        asset_class="us_option",
        side="long",
        quantity=Decimal("1"),
        average_entry_price=Decimal("2"),
        cost_basis=Decimal("200"),
        unrealized_pl=Decimal("0"),
        as_of=NOW,
    )


def order(order_id: str) -> BrokerOrder:
    return BrokerOrder(
        broker_order_id=order_id,
        client_order_id=f"client-{order_id}",
        status="accepted",
        asset_class="us_option",
        symbol="NVDA260918C00120000",
        side="buy",
        order_type="limit",
        order_class="simple",
        time_in_force="day",
        quantity=Decimal("1"),
        filled_quantity=Decimal("0"),
        created_at=NOW,
    )


class FakeAdapter:
    def __init__(self, snapshot: ReconciliationSnapshot | None = None) -> None:
        self.snapshot = snapshot

    async def reconcile(self) -> ReconciliationSnapshot:
        if self.snapshot is None:
            raise ConnectionError("paper API unavailable")
        return self.snapshot


@pytest.mark.asyncio
async def test_reconciliation_replaces_divergent_local_state_with_broker_state() -> None:
    store = MemoryBrokerProjectionStore()
    old = ReconciliationSnapshot(
        account=account(),
        positions=(position("old"),),
        open_orders=(order("old"),),
        reconciled_at=NOW,
    )
    await store.apply_reconciliation(old)
    broker = ReconciliationSnapshot(
        account=account(),
        positions=(position("broker"),),
        open_orders=(order("broker"),),
        reconciled_at=NOW,
    )

    divergence = await ReconciliationService(FakeAdapter(broker), store).reconcile()  # type: ignore[arg-type]

    assert divergence == 4
    assert {item.asset_id for item in await store.list_positions()} == {"broker"}
    assert {item.broker_order_id for item in await store.list_orders()} == {"broker"}
    assert (await store.get_status()).state is BrokerState.RECONCILED


@pytest.mark.asyncio
async def test_reconciliation_preserves_independent_stream_connection_state() -> None:
    store = MemoryBrokerProjectionStore()
    await store.set_stream_connected(True)
    broker = ReconciliationSnapshot(
        account=account(), positions=(), open_orders=(), reconciled_at=NOW
    )

    await ReconciliationService(FakeAdapter(broker), store).reconcile()  # type: ignore[arg-type]

    status = await store.get_status()
    assert status.state is BrokerState.RECONCILED
    assert status.stream_connected is True


@pytest.mark.asyncio
async def test_failed_reconciliation_blocks_execution() -> None:
    store = MemoryBrokerProjectionStore()
    with pytest.raises(ConnectionError):
        await ReconciliationService(FakeAdapter(), store).reconcile()  # type: ignore[arg-type]
    status = await store.get_status()
    assert status.state is BrokerState.UNKNOWN
    assert "ConnectionError" in (status.failure_reason or "")


@pytest.mark.asyncio
async def test_execution_gate_requires_fresh_reconciliation_and_stream() -> None:
    store = MemoryBrokerProjectionStore()
    snapshot = ReconciliationSnapshot(
        account=account(), positions=(), open_orders=(), reconciled_at=NOW
    )
    await store.apply_reconciliation(snapshot)
    gate = BrokerExecutionGate(store, maximum_reconciliation_age=timedelta(seconds=90))

    disconnected = await gate.evaluate(NOW + timedelta(seconds=10))
    await store.set_stream_connected(True)
    allowed = await gate.evaluate(NOW + timedelta(seconds=10))
    stale = await gate.evaluate(NOW + timedelta(seconds=91))

    assert disconnected.allowed is False
    assert allowed.allowed is True
    assert stale.allowed is False
    assert "stale" in stale.reason.lower()
