from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict

from packages.broker.adapter import BrokerAdapter
from packages.broker.projections import BrokerProjectionStore
from packages.domain.system import BrokerState
from packages.observability.logging import get_logger

logger = get_logger(__name__)


class ExecutionGateDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str


class BrokerExecutionGate:
    def __init__(
        self,
        projections: BrokerProjectionStore,
        *,
        maximum_reconciliation_age: timedelta = timedelta(seconds=90),
    ) -> None:
        self._projections = projections
        self._maximum_age = maximum_reconciliation_age

    async def evaluate(self, now: datetime | None = None) -> ExecutionGateDecision:
        evaluated_at = now or datetime.now(UTC)
        status = await self._projections.get_status()
        if status.state is not BrokerState.RECONCILED:
            return ExecutionGateDecision(
                allowed=False,
                reason=f"Broker state is {status.state.value}; reconciliation is required.",
            )
        if status.last_reconciled_at is None:
            return ExecutionGateDecision(
                allowed=False, reason="Reconciliation timestamp is unknown."
            )
        if evaluated_at - status.last_reconciled_at > self._maximum_age:
            return ExecutionGateDecision(allowed=False, reason="Broker reconciliation is stale.")
        if not status.stream_connected:
            return ExecutionGateDecision(
                allowed=False,
                reason="Alpaca trade_updates stream is not connected.",
            )
        account = await self._projections.get_account()
        if account is None:
            return ExecutionGateDecision(
                allowed=False, reason="Broker account projection is absent."
            )
        if account.account_blocked or account.trading_blocked or account.trade_suspended_by_user:
            return ExecutionGateDecision(
                allowed=False, reason="Alpaca account is blocked or suspended."
            )
        return ExecutionGateDecision(allowed=True, reason="Broker state is known and reconciled.")


class ReconciliationService:
    def __init__(self, adapter: BrokerAdapter, projections: BrokerProjectionStore) -> None:
        self._adapter = adapter
        self._projections = projections

    async def reconcile(self) -> int:
        await self._projections.mark_state(BrokerState.RECONCILING)
        try:
            snapshot = await self._adapter.reconcile()
            divergence_count = await self._projections.apply_reconciliation(snapshot)
        except Exception as error:
            await self._projections.mark_state(
                BrokerState.UNKNOWN,
                f"Reconciliation failed: {type(error).__name__}",
            )
            logger.exception(
                "broker_reconciliation_failed", extra={"event": "broker_reconciliation_failed"}
            )
            raise
        logger.info(
            "broker_reconciliation_completed",
            extra={
                "event": "broker_reconciliation_completed",
                "divergence_count": divergence_count,
                "position_count": len(snapshot.positions),
                "order_count": len(snapshot.open_orders),
            },
        )
        return divergence_count

    async def consume_trade_updates(self) -> None:
        await self._projections.set_stream_connected(True)
        try:
            async for update in self._adapter.trade_updates():
                await self._projections.apply_trade_update(update)
        except Exception:
            await self._projections.set_stream_connected(False)
            await self._projections.mark_state(
                BrokerState.UNKNOWN,
                "Alpaca trade_updates stream disconnected.",
            )
            logger.exception(
                "trade_updates_disconnected", extra={"event": "trade_updates_disconnected"}
            )
            raise
        finally:
            await self._projections.set_stream_connected(False)
