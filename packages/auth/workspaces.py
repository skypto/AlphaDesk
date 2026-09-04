from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.auth.invitations import DEFAULT_WATCHLIST
from packages.database.models import (
    AppUserRecord,
    AuditRecord,
    WatchlistSymbolRecord,
    WorkspaceRecord,
)


@dataclass(frozen=True)
class WorkspaceProvisioningResult:
    workspace: WorkspaceRecord
    created: bool


async def create_connected_workspace(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    owner_email: str,
    actor_user_id: UUID,
    audit_action: str,
) -> WorkspaceRecord:
    """Create the complete local workspace aggregate inside an existing transaction."""
    now = datetime.now(UTC)
    workspace = WorkspaceRecord(
        workspace_id=uuid4(),
        owner_user_id=owner_user_id,
        name=f"{owner_email.split('@', 1)[0]}'s paper desk",
        workspace_type="CONNECTED_PAPER",
        status="ONBOARDING",
        scanner_enabled=False,
        created_at=now,
        updated_at=now,
    )
    session.add(workspace)
    await session.flush()
    session.add_all(
        WatchlistSymbolRecord(
            workspace_id=workspace.workspace_id,
            symbol=symbol,
            created_at=now,
        )
        for symbol in DEFAULT_WATCHLIST
    )
    session.add(
        AuditRecord(
            audit_id=uuid4(),
            workspace_id=workspace.workspace_id,
            actor_user_id=actor_user_id,
            action=audit_action,
            detail={"status": "ONBOARDING", "watchlist_count": len(DEFAULT_WATCHLIST)},
            occurred_at=now,
        )
    )
    return workspace


class AdminWorkspaceProvisioningService:
    """Idempotently provision a workspace for the authenticated administrator only."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def provision(self, admin_user_id: UUID) -> WorkspaceProvisioningResult:
        async with self._sessions.begin() as session:
            admin = await session.scalar(
                select(AppUserRecord)
                .where(AppUserRecord.user_id == admin_user_id)
                .with_for_update()
            )
            if admin is None or not admin.is_admin:
                raise PermissionError("Administrator access required")

            existing = await session.scalar(
                select(WorkspaceRecord).where(
                    WorkspaceRecord.owner_user_id == admin_user_id
                )
            )
            if existing is not None:
                return WorkspaceProvisioningResult(workspace=existing, created=False)

            workspace = await create_connected_workspace(
                session,
                owner_user_id=admin.user_id,
                owner_email=admin.email,
                actor_user_id=admin.user_id,
                audit_action="ADMIN_CONNECTED_WORKSPACE_PROVISIONED",
            )
            return WorkspaceProvisioningResult(workspace=workspace, created=True)
