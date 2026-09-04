from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete

from packages.connected.opportunities import complete_scan_run, start_scan_run
from packages.database.models import AppUserRecord, ConnectedScanRunRecord, WorkspaceRecord
from packages.database.session import Database

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("ALPHADESK_RUN_INTEGRATION") != "1",
        reason="Set ALPHADESK_RUN_INTEGRATION=1 to use local PostgreSQL.",
    ),
]

USER_ID = UUID("94000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("94000000-0000-0000-0000-000000000002")


@pytest.mark.asyncio
async def test_scan_run_counts_are_persisted_per_workspace() -> None:
    database = Database(
        os.getenv(
            "ALPHADESK_TEST_DATABASE_URL",
            "postgresql+psycopg://alphadesk:alphadesk_dev@localhost:5432/alphadesk",
        )
    )
    now = datetime.now(UTC)
    try:
        async with database.sessions.begin() as session:
            session.add(
                AppUserRecord(
                    user_id=USER_ID,
                    auth_subject="scan-run-integration",
                    email="scan-run@example.test",
                    is_admin=False,
                    created_at=now,
                    last_seen_at=now,
                )
            )
            session.add(
                WorkspaceRecord(
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    name="Scan run integration",
                    workspace_type="CONNECTED_PAPER",
                    status="ACTIVE",
                    scanner_enabled=False,
                    created_at=now,
                    updated_at=now,
                )
            )

        started = await start_scan_run(
            database.sessions, WORKSPACE_ID, trigger="MANUAL", attempted_count=7
        )
        completed = await complete_scan_run(
            database.sessions, started.scan_run_id, completed_count=5, failed_count=2
        )

        assert completed.workspace_id == WORKSPACE_ID
        assert completed.completed_at is not None
        assert completed.completed_count == 5
        assert completed.failed_count == 2
    finally:
        async with database.sessions.begin() as session:
            await session.execute(
                delete(ConnectedScanRunRecord).where(
                    ConnectedScanRunRecord.workspace_id == WORKSPACE_ID
                )
            )
            await session.execute(
                delete(WorkspaceRecord).where(WorkspaceRecord.workspace_id == WORKSPACE_ID)
            )
            await session.execute(delete(AppUserRecord).where(AppUserRecord.user_id == USER_ID))
        await database.close()
