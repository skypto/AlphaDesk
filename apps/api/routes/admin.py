from __future__ import annotations

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from packages.auth.dependencies import AuthPrincipal, require_admin
from packages.auth.invitations import InvitationService
from packages.auth.workspaces import AdminWorkspaceProvisioningService
from packages.database.models import InvitationRecord, WatchlistSymbolRecord

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateInvitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    comment: str = Field(default="", max_length=240)
    max_uses: int = Field(default=1, ge=1, le=100)
    expires_in_days: int | None = Field(default=7, ge=1, le=90)


class InvitationAdminView(BaseModel):
    model_config = ConfigDict(frozen=True)

    invitation_id: UUID
    comment: str
    max_uses: int
    use_count: int
    expires_at: datetime | None
    disabled_at: datetime | None
    created_at: datetime
    invitation_code: str | None = None


class AdminWorkspaceProvisionView(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: UUID
    status: str
    created: bool
    watchlist_count: int


def _view(record: InvitationRecord, token: str | None = None) -> InvitationAdminView:
    return InvitationAdminView(
        invitation_id=record.invitation_id,
        comment=record.comment,
        max_uses=record.max_uses,
        use_count=record.use_count,
        expires_at=record.expires_at,
        disabled_at=record.disabled_at,
        created_at=record.created_at,
        invitation_code=token,
    )


@router.post("/workspace", response_model=AdminWorkspaceProvisionView)
async def provision_admin_workspace(
    request: Request,
    admin: AuthPrincipal = Depends(require_admin),
) -> AdminWorkspaceProvisionView:
    result = await AdminWorkspaceProvisioningService(
        request.app.state.database.sessions
    ).provision(admin.user_id)
    async with request.app.state.database.sessions() as session:
        watchlist_count = len(
            tuple(
                await session.scalars(
                    select(WatchlistSymbolRecord.symbol).where(
                        WatchlistSymbolRecord.workspace_id
                        == result.workspace.workspace_id
                    )
                )
            )
        )
    return AdminWorkspaceProvisionView(
        workspace_id=result.workspace.workspace_id,
        status=result.workspace.status,
        created=result.created,
        watchlist_count=watchlist_count,
    )


@router.post("/invitations", response_model=InvitationAdminView)
async def create_invitation(
    payload: CreateInvitation,
    request: Request,
    admin: AuthPrincipal = Depends(require_admin),
) -> InvitationAdminView:
    expires_at = (
        None
        if payload.expires_in_days is None
        else datetime.now(UTC) + timedelta(days=payload.expires_in_days)
    )
    record, token = await InvitationService(request.app.state.database.sessions).create(
        created_by_user_id=admin.user_id,
        comment=payload.comment,
        max_uses=payload.max_uses,
        expires_at=expires_at,
    )
    return _view(record, token)


@router.get("/invitations", response_model=list[InvitationAdminView])
async def list_invitations(
    request: Request, _: AuthPrincipal = Depends(require_admin)
) -> list[InvitationAdminView]:
    async with request.app.state.database.sessions() as session:
        records = await session.scalars(
            select(InvitationRecord).order_by(InvitationRecord.created_at.desc())
        )
        return [_view(record) for record in records]


@router.delete("/invitations/{invitation_id}", response_model=InvitationAdminView)
async def disable_invitation(
    invitation_id: UUID,
    request: Request,
    _: AuthPrincipal = Depends(require_admin),
) -> InvitationAdminView:
    async with request.app.state.database.sessions.begin() as session:
        record = await session.get(InvitationRecord, invitation_id, with_for_update=True)
        if record is None:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if record.disabled_at is None:
            record.disabled_at = datetime.now(UTC)
        return _view(record)
