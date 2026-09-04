from __future__ import annotations

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from packages.auth.dependencies import AuthPrincipal, require_principal
from packages.database.models import WorkspaceRecord

router = APIRouter(tags=["identity"])


class IdentityView(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    is_admin: bool
    workspace_id: UUID | None
    workspace_status: str | None


@router.get("/identity/me", response_model=IdentityView)
async def identity_me(
    request: Request, principal: AuthPrincipal = Depends(require_principal)
) -> IdentityView:
    async with request.app.state.database.sessions() as session:
        workspace = await session.scalar(
            select(WorkspaceRecord).where(WorkspaceRecord.owner_user_id == principal.user_id)
        )
    return IdentityView(
        email=principal.email,
        is_admin=principal.is_admin,
        workspace_id=None if workspace is None else workspace.workspace_id,
        workspace_status=None if workspace is None else workspace.status,
    )
