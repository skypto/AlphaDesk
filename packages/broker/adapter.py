from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from packages.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    BrokerTradeUpdate,
    OrderSubmission,
    ReconciliationSnapshot,
)


class BrokerAdapter(Protocol):
    async def get_account(self) -> BrokerAccount: ...

    async def list_positions(self) -> tuple[BrokerPosition, ...]: ...

    async def list_open_orders(self) -> tuple[BrokerOrder, ...]: ...

    async def submit_order(self, order: OrderSubmission) -> BrokerOrder: ...

    async def cancel_order(self, broker_order_id: str) -> None: ...

    async def get_order(
        self,
        *,
        broker_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> BrokerOrder | None: ...

    async def reconcile(self) -> ReconciliationSnapshot: ...

    def trade_updates(self) -> AsyncIterator[BrokerTradeUpdate]: ...

    async def close_position(self, symbol_or_asset_id: str) -> BrokerOrder: ...

    async def close(self) -> None: ...
