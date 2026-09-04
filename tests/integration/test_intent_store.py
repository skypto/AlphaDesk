from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete

from packages.database.models import AppUserRecord, OrderIntentRecord, WorkspaceRecord
from packages.database.session import Database
from packages.domain.workflow import OrderIntent
from packages.execution.engine import ExecutionState
from packages.execution.store import PostgresIntentStore
from packages.replay.catalyst import run_catalyst_replay

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("ALPHADESK_RUN_INTEGRATION") != "1",
        reason="Set ALPHADESK_RUN_INTEGRATION=1 to use local PostgreSQL.",
    ),
]

USER_ID = UUID("90000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("90000000-0000-0000-0000-000000000002")


@pytest.mark.asyncio
async def test_order_intent_reservation_is_atomic_and_idempotent() -> None:
    database = Database(
        os.getenv(
            "ALPHADESK_TEST_DATABASE_URL",
            "postgresql+psycopg://alphadesk:alphadesk_dev@localhost:5432/alphadesk",
        )
    )
    now = datetime.now(UTC)
    async with database.sessions.begin() as session:
        session.add(
            AppUserRecord(
                user_id=USER_ID,
                auth_subject="integration-intent-user",
                email="intent-integration@example.test",
                is_admin=False,
                created_at=now,
                last_seen_at=now,
            )
        )
        session.add(
            WorkspaceRecord(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                name="Intent integration",
                workspace_type="CONNECTED_PAPER",
                status="ACTIVE",
                scanner_enabled=False,
                created_at=now,
                updated_at=now,
            )
        )
    store = PostgresIntentStore(database.sessions, WORKSPACE_ID)
    replay = run_catalyst_replay("approved")
    assert replay.order_intent is not None
    intent = OrderIntent.model_validate(replay.order_intent)
    try:
        assert await store.reserve_submission(intent)
        assert not await store.reserve_submission(intent)
        assert await store.get_state(intent.client_order_id) is ExecutionState.SUBMISSION_STARTED
        await store.set_state(intent.client_order_id, ExecutionState.ACCEPTED)
        assert await store.get_state(intent.client_order_id) is ExecutionState.ACCEPTED
    finally:
        async with database.sessions.begin() as session:
            await session.execute(delete(OrderIntentRecord))
            await session.execute(delete(WorkspaceRecord))
            await session.execute(delete(AppUserRecord))
        await database.close()
