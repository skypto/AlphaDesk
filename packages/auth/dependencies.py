from __future__ import annotations

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from packages.auth.jwt import AuthenticationError, VerifiedIdentity
from packages.database.models import AppUserRecord, WorkspaceRecord

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: UUID
    auth_subject: str
    email: str
    is_admin: bool


@dataclass(frozen=True)
class WorkspaceContext:
    principal: AuthPrincipal
    workspace_id: UUID
    status: str


async def _sync_user(request: Request, identity: VerifiedIdentity) -> AuthPrincipal:
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Authentication requires infrastructure")
    now = datetime.now(UTC)
    is_bootstrap_admin = identity.email in request.app.state.settings.admin_emails
    async with database.sessions.begin() as session:
        record = await session.scalar(
            select(AppUserRecord).where(AppUserRecord.auth_subject == identity.subject)
        )
        if record is None:
            record = AppUserRecord(
                user_id=uuid4(),
                auth_subject=identity.subject,
                email=identity.email,
                is_admin=is_bootstrap_admin,
                created_at=now,
                last_seen_at=now,
            )
            session.add(record)
            await session.flush()
        else:
            record.email = identity.email
            record.last_seen_at = now
            if is_bootstrap_admin:
                record.is_admin = True
        return AuthPrincipal(
            user_id=record.user_id,
            auth_subject=record.auth_subject,
            email=record.email,
            is_admin=record.is_admin,
        )


async def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    verifier = request.app.state.auth_verifier
    if verifier is None:
        raise HTTPException(
            status_code=503, detail="Connected workspace authentication is disabled"
        )
    try:
        identity = await verifier.verify(credentials.credentials)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return await _sync_user(request, identity)


async def require_admin(principal: AuthPrincipal = Depends(require_principal)) -> AuthPrincipal:
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return principal


async def require_workspace(
    request: Request,
    principal: AuthPrincipal = Depends(require_principal),
) -> WorkspaceContext:
    database = request.app.state.database
    assert database is not None
    async with database.sessions() as session:
        workspace = await session.scalar(
            select(WorkspaceRecord).where(WorkspaceRecord.owner_user_id == principal.user_id)
        )
    if workspace is None:
        raise HTTPException(
            status_code=403,
            detail="No Connected Paper Workspace has been provisioned for this account.",
        )
    if workspace.status == "SUSPENDED":
        raise HTTPException(status_code=423, detail="Connected workspace is suspended")
    return WorkspaceContext(
        principal=principal, workspace_id=workspace.workspace_id, status=workspace.status
    )
