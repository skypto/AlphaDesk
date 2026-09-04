from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

from packages.auth.invitations import DEFAULT_WATCHLIST
from packages.auth.workspaces import AdminWorkspaceProvisioningService
from packages.database.models import (
    AppUserRecord,
    AuditRecord,
    WatchlistSymbolRecord,
    WorkspaceRecord,
)
from packages.database.session import Database

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("ALPHADESK_RUN_INTEGRATION") != "1",
        reason="Set ALPHADESK_RUN_INTEGRATION=1 to use local PostgreSQL.",
    ),
]

ADMIN_ID = UUID("93000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_admin_workspace_provisioning_is_complete_and_idempotent() -> None:
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
                    user_id=ADMIN_ID,
                    auth_subject="admin-workspace-integration",
                    email="workspace-admin@example.test",
                    is_admin=True,
                    created_at=now,
                    last_seen_at=now,
                )
            )

        service = AdminWorkspaceProvisioningService(database.sessions)
        first = await service.provision(ADMIN_ID)
        second = await service.provision(ADMIN_ID)

        async with database.sessions() as session:
            workspace_count = await session.scalar(
                select(func.count())
                .select_from(WorkspaceRecord)
                .where(WorkspaceRecord.owner_user_id == ADMIN_ID)
            )
            watchlist_count = await session.scalar(
                select(func.count())
                .select_from(WatchlistSymbolRecord)
                .where(WatchlistSymbolRecord.workspace_id == first.workspace.workspace_id)
            )
            audit_count = await session.scalar(
                select(func.count())
                .select_from(AuditRecord)
                .where(
                    AuditRecord.workspace_id == first.workspace.workspace_id,
                    AuditRecord.action == "ADMIN_CONNECTED_WORKSPACE_PROVISIONED",
                )
            )

        assert first.created is True
        assert second.created is False
        assert second.workspace.workspace_id == first.workspace.workspace_id
        assert first.workspace.status == "ONBOARDING"
        assert workspace_count == 1
        assert watchlist_count == len(DEFAULT_WATCHLIST)
        assert audit_count == 1
    finally:
        async with database.sessions.begin() as session:
            workspace_ids = select(WorkspaceRecord.workspace_id).where(
                WorkspaceRecord.owner_user_id == ADMIN_ID
            )
            await session.execute(
                delete(AuditRecord).where(AuditRecord.workspace_id.in_(workspace_ids))
            )
            await session.execute(
                delete(WatchlistSymbolRecord).where(
                    WatchlistSymbolRecord.workspace_id.in_(workspace_ids)
                )
            )
            await session.execute(
                delete(WorkspaceRecord).where(WorkspaceRecord.owner_user_id == ADMIN_ID)
            )
            await session.execute(delete(AppUserRecord).where(AppUserRecord.user_id == ADMIN_ID))
        await database.close()
