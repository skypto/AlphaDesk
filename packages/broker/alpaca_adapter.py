from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, LimitOrderRequest, OptionLegRequest
from alpaca.trading.stream import TradingStream

from packages.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerOrderLeg,
    BrokerPosition,
    BrokerTradeUpdate,
    OrderSubmission,
    ReconciliationSnapshot,
)


def _text(value: object | None, default: str = "") -> str:
    if value is None:
        return default
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _decimal(value: object | None, default: str = "0") -> Decimal:
    return Decimal(default if value is None else str(value))


def _optional_decimal(value: object | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _datetime(value: object | None, *, default_now: bool = False) -> datetime | None:
    if value is None:
        return datetime.now(UTC) if default_now else None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _required_datetime(value: object | None) -> datetime:
    mapped = _datetime(value, default_now=True)
    assert mapped is not None
    return mapped


class AlpacaPaperBrokerAdapter:
    """The sole Alpaca SDK boundary. It always constructs paper clients."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        *,
        trading_client: Any | None = None,
        trading_stream: Any | None = None,
    ) -> None:
        if not api_key or not secret_key:
            raise ValueError("Paper Alpaca credentials are required for the broker adapter.")
        self._client = trading_client or TradingClient(api_key, secret_key, paper=True)
        self._stream = trading_stream or TradingStream(api_key, secret_key, paper=True)
        self._stream_task: asyncio.Task[None] | None = None

    @staticmethod
    def _map_account(raw: Any) -> BrokerAccount:
        return BrokerAccount(
            account_id=_text(raw.id),
            account_number=_text(raw.account_number),
            status=_text(raw.status),
            currency=_text(raw.currency, "USD"),
            equity=_decimal(raw.equity),
            cash=_decimal(raw.cash),
            buying_power=_decimal(raw.buying_power),
            options_buying_power=_optional_decimal(raw.options_buying_power),
            last_equity=_decimal(raw.last_equity),
            trading_blocked=bool(raw.trading_blocked),
            account_blocked=bool(raw.account_blocked),
            trade_suspended_by_user=bool(raw.trade_suspended_by_user),
        )

    @staticmethod
    def _map_position(raw: Any) -> BrokerPosition:
        return BrokerPosition(
            asset_id=_text(raw.asset_id),
            symbol=_text(raw.symbol),
            asset_class=_text(raw.asset_class),
            side=_text(raw.side),
            quantity=_decimal(raw.qty),
            quantity_available=_optional_decimal(raw.qty_available),
            average_entry_price=_decimal(raw.avg_entry_price),
            market_value=_optional_decimal(raw.market_value),
            cost_basis=_decimal(raw.cost_basis),
            unrealized_pl=_decimal(raw.unrealized_pl),
            current_price=_optional_decimal(raw.current_price),
        )

    @classmethod
    def _map_order(cls, raw: Any) -> BrokerOrder:
        legs = tuple(
            BrokerOrderLeg(
                broker_order_id=_text(leg.id),
                symbol=_text(leg.symbol),
                side=_text(leg.side),
                quantity=_optional_decimal(leg.qty),
                filled_quantity=_decimal(leg.filled_qty),
                status=_text(leg.status, "unknown"),
            )
            for leg in (raw.legs or [])
        )
        return BrokerOrder(
            broker_order_id=_text(raw.id),
            client_order_id=_text(raw.client_order_id),
            status=_text(raw.status, "unknown"),
            asset_class=_text(raw.asset_class),
            symbol=_text(raw.symbol) or None,
            side=_text(raw.side) or None,
            order_type=_text(raw.order_type or raw.type),
            order_class=_text(raw.order_class, "simple"),
            time_in_force=_text(raw.time_in_force),
            quantity=_optional_decimal(raw.qty),
            filled_quantity=_decimal(raw.filled_qty),
            filled_average_price=_optional_decimal(raw.filled_avg_price),
            limit_price=_optional_decimal(raw.limit_price),
            submitted_at=_datetime(raw.submitted_at),
            created_at=_required_datetime(raw.created_at),
            updated_at=_datetime(raw.updated_at),
            legs=legs,
        )

    @classmethod
    def _map_trade_update(cls, raw: Any) -> BrokerTradeUpdate:
        return BrokerTradeUpdate(
            event=_text(raw.event),
            order=cls._map_order(raw.order),
            execution_id=_text(raw.execution_id) or None,
            price=_optional_decimal(raw.price),
            quantity=_optional_decimal(raw.qty),
            position_quantity=_optional_decimal(raw.position_qty),
            occurred_at=_required_datetime(raw.timestamp),
        )

    async def get_account(self) -> BrokerAccount:
        raw = await asyncio.to_thread(self._client.get_account)
        return self._map_account(raw)

    async def list_positions(self) -> tuple[BrokerPosition, ...]:
        raw = await asyncio.to_thread(self._client.get_all_positions)
        return tuple(self._map_position(position) for position in raw)

    async def list_open_orders(self) -> tuple[BrokerOrder, ...]:
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN, nested=True)
        raw = await asyncio.to_thread(self._client.get_orders, request)
        return tuple(self._map_order(order) for order in raw)

    async def submit_order(self, order: OrderSubmission) -> BrokerOrder:
        request = LimitOrderRequest(
            qty=order.quantity,
            limit_price=float(order.limit_price),
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.MLEG,
            client_order_id=order.client_order_id,
            legs=[
                OptionLegRequest(
                    symbol=leg.symbol,
                    ratio_qty=leg.ratio,
                    side=OrderSide.BUY if leg.side == "buy" else OrderSide.SELL,
                )
                for leg in order.legs
            ],
        )
        raw = await asyncio.to_thread(self._client.submit_order, request)
        return self._map_order(raw)

    async def cancel_order(self, broker_order_id: str) -> None:
        await asyncio.to_thread(self._client.cancel_order_by_id, broker_order_id)

    async def close_position(self, symbol_or_asset_id: str) -> BrokerOrder:
        raw = await asyncio.to_thread(self._client.close_position, symbol_or_asset_id)
        return self._map_order(raw)

    async def get_order(
        self,
        *,
        broker_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> BrokerOrder | None:
        if (broker_order_id is None) == (client_order_id is None):
            raise ValueError("Provide exactly one broker_order_id or client_order_id.")
        try:
            if broker_order_id is not None:
                raw = await asyncio.to_thread(self._client.get_order_by_id, broker_order_id)
            else:
                assert client_order_id is not None
                raw = await asyncio.to_thread(self._client.get_order_by_client_id, client_order_id)
        except APIError as error:
            if getattr(error, "status_code", None) == 404:
                return None
            raise
        return self._map_order(raw)

    async def reconcile(self) -> ReconciliationSnapshot:
        account = await self.get_account()
        positions = await self.list_positions()
        orders = await self.list_open_orders()
        return ReconciliationSnapshot(account=account, positions=positions, open_orders=orders)

    async def _run_stream(self) -> None:
        await asyncio.to_thread(self._stream.run)

    async def trade_updates(self) -> AsyncIterator[BrokerTradeUpdate]:
        queue: asyncio.Queue[BrokerTradeUpdate] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        async def handler(raw: Any) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, self._map_trade_update(raw))

        self._stream.subscribe_trade_updates(handler)
        self._stream_task = asyncio.create_task(self._run_stream(), name="alpaca-trade-updates")
        try:
            while True:
                yield await queue.get()
        finally:
            await self.close()

    async def close(self) -> None:
        if self._stream_task is None:
            return
        await asyncio.to_thread(self._stream.stop)
        try:
            await asyncio.wait_for(self._stream_task, timeout=5)
        except TimeoutError:
            self._stream_task.cancel()
        self._stream_task = None
