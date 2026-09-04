from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Protocol

from packages.broker.adapter import BrokerAdapter
from packages.domain.broker import BrokerOrder, OrderSubmission, SubmissionLeg
from packages.domain.workflow import OrderIntent


class ExecutionState(StrEnum):
    CREATED = "CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    SUBMISSION_STARTED = "SUBMISSION_STARTED"
    SUBMISSION_UNCERTAIN = "SUBMISSION_UNCERTAIN"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"


class DuplicateSubmission(RuntimeError):
    pass


class ExecutionBlocked(RuntimeError):
    pass


class ExecutionPreflight(Protocol):
    async def execution_allowed(self) -> tuple[bool, str]: ...


class IntentStore(Protocol):
    async def reserve_submission(self, intent: OrderIntent) -> bool: ...

    async def set_state(self, client_order_id: str, state: ExecutionState) -> None: ...

    async def get_state(self, client_order_id: str) -> ExecutionState | None: ...


class InMemoryIntentStore:
    def __init__(self) -> None:
        self.states: dict[str, ExecutionState] = {}
        self._lock = asyncio.Lock()

    async def reserve_submission(self, intent: OrderIntent) -> bool:
        async with self._lock:
            if intent.client_order_id in self.states:
                return False
            self.states[intent.client_order_id] = ExecutionState.SUBMISSION_STARTED
            return True

    async def set_state(self, client_order_id: str, state: ExecutionState) -> None:
        self.states[client_order_id] = state

    async def get_state(self, client_order_id: str) -> ExecutionState | None:
        return self.states.get(client_order_id)


class ExecutionEngine:
    """The only application service authorized to submit through BrokerAdapter."""

    def __init__(
        self,
        adapter: BrokerAdapter,
        store: IntentStore,
        *,
        preflight: ExecutionPreflight | None = None,
    ) -> None:
        self._adapter = adapter
        self._store = store
        self._preflight = preflight

    async def execute(self, intent: OrderIntent) -> BrokerOrder:
        if self._preflight is not None:
            allowed, reason = await self._preflight.execution_allowed()
            if not allowed:
                raise ExecutionBlocked(reason)
        reserved = await self._store.reserve_submission(intent)
        if not reserved:
            raise DuplicateSubmission(f"Intent {intent.client_order_id} was already submitted")
        submission = OrderSubmission(
            client_order_id=intent.client_order_id,
            quantity=intent.quantity,
            limit_price=intent.limit_price,
            time_in_force=intent.time_in_force,
            legs=tuple(
                SubmissionLeg(symbol=leg.symbol, side=leg.side, ratio=leg.ratio)
                for leg in intent.legs
            ),
        )
        try:
            order = await self._adapter.submit_order(submission)
        except Exception:
            await self._store.set_state(intent.client_order_id, ExecutionState.SUBMISSION_UNCERTAIN)
            raise
        await self._store.set_state(intent.client_order_id, ExecutionState.ACCEPTED)
        return order

    async def reconcile_uncertain(self, intent: OrderIntent) -> BrokerOrder | None:
        state = await self._store.get_state(intent.client_order_id)
        if state is not ExecutionState.SUBMISSION_UNCERTAIN:
            raise ValueError("Only uncertain submissions may be reconciled")
        order = await self._adapter.get_order(client_order_id=intent.client_order_id)
        if order is not None:
            await self._store.set_state(intent.client_order_id, ExecutionState.ACCEPTED)
        return order
