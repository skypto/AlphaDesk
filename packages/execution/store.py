from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.database.models import OrderIntentRecord
from packages.domain.workflow import OrderIntent
from packages.execution.engine import ExecutionState


class PostgresIntentStore:
    """Atomic idempotency reservation backed by the unique client-order ID."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], workspace_id: UUID) -> None:
        self._sessions = sessions
        self._workspace_id = workspace_id

    async def reserve_submission(self, intent: OrderIntent) -> bool:
        now = datetime.now(UTC)
        statement = (
            insert(OrderIntentRecord)
            .values(
                order_intent_id=intent.order_intent_id,
                workspace_id=self._workspace_id,
                client_order_id=intent.client_order_id,
                risk_decision_id=intent.risk_decision_id,
                state=ExecutionState.SUBMISSION_STARTED.value,
                payload=intent.model_dump(mode="json"),
                created_at=intent.created_at,
                updated_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_order_intent_workspace_client")
            .returning(OrderIntentRecord.client_order_id)
        )
        async with self._sessions.begin() as session:
            return (await session.scalar(statement)) is not None

    async def set_state(self, client_order_id: str, state: ExecutionState) -> None:
        statement = (
            update(OrderIntentRecord)
            .where(
                OrderIntentRecord.workspace_id == self._workspace_id,
                OrderIntentRecord.client_order_id == client_order_id,
            )
            .values(state=state.value, updated_at=datetime.now(UTC))
            .returning(OrderIntentRecord.client_order_id)
        )
        async with self._sessions.begin() as session:
            if await session.scalar(statement) is None:
                raise KeyError(client_order_id)

    async def get_state(self, client_order_id: str) -> ExecutionState | None:
        async with self._sessions() as session:
            value = await session.scalar(
                select(OrderIntentRecord.state).where(
                    OrderIntentRecord.workspace_id == self._workspace_id,
                    OrderIntentRecord.client_order_id == client_order_id,
                )
            )
            return None if value is None else ExecutionState(value)
