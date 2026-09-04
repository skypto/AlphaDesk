from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

from packages.auth.invitations import DEFAULT_WATCHLIST, InvitationService
from packages.auth.registration import RegistrationService
from packages.auth.supabase_admin import SupabaseIdentity
from packages.database.models import (
    AppUserRecord,
    InvitationRecord,
    InvitationRedemptionRecord,
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

ADMIN_ID = UUID("92000000-0000-0000-0000-000000000001")


class FakeSupabaseAdmin:
    created: list[str]
    deleted: list[str]

    def __init__(self) -> None:
        self.created = []
        self.deleted = []

    async def create_user(self, email: str, password: str) -> SupabaseIdentity:
        assert password == "integration-password"
        self.created.append(email)
        return SupabaseIdentity(
            subject="92000000-0000-0000-0000-000000000099",
            email=email,
        )

    async def delete_user(self, subject: str) -> None:
        self.deleted.append(subject)


@pytest.mark.asyncio
async def test_valid_code_creates_one_tenant_and_consumes_one_use() -> None:
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
                user_id=ADMIN_ID,
                auth_subject="registration-integration-admin",
                email="registration-admin@example.test",
                is_admin=True,
                created_at=now,
                last_seen_at=now,
            )
        )
    invitation, code = await InvitationService(database.sessions).create(
        created_by_user_id=ADMIN_ID,
        comment="Registration integration",
    )
    supabase = FakeSupabaseAdmin()
    try:
        workspace = await RegistrationService(
            database.sessions,
            supabase,  # type: ignore[arg-type]
            frozenset({"registration-admin@example.test"}),
        ).register("OPERATOR@example.test", "integration-password", code.lower())

        async with database.sessions() as session:
            stored_invitation = await session.get(InvitationRecord, invitation.invitation_id)
            redemptions = await session.scalar(
                select(func.count())
                .select_from(InvitationRedemptionRecord)
                .where(InvitationRedemptionRecord.invitation_id == invitation.invitation_id)
            )
            watchlist = await session.scalar(
                select(func.count())
                .select_from(WatchlistSymbolRecord)
                .where(WatchlistSymbolRecord.workspace_id == workspace.workspace_id)
            )
        assert stored_invitation is not None and stored_invitation.use_count == 1
        assert redemptions == 1
        assert watchlist == len(DEFAULT_WATCHLIST)
        assert supabase.created == ["operator@example.test"]
        assert supabase.deleted == []
    finally:
        async with database.sessions.begin() as session:
            await session.execute(delete(InvitationRedemptionRecord))
            await session.execute(delete(WatchlistSymbolRecord))
            await session.execute(delete(WorkspaceRecord))
            await session.execute(delete(InvitationRecord))
            await session.execute(delete(AppUserRecord).where(AppUserRecord.user_id == ADMIN_ID))
            await session.execute(
                delete(AppUserRecord).where(AppUserRecord.email == "operator@example.test")
            )
        await database.close()
