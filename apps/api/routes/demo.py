from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict

from packages.database.models import DemoSessionRecord
from packages.demo.sessions import InvalidDemoSession
from packages.replay.catalyst import CatalystReplay, ReplayScenario, run_catalyst_replay

router = APIRouter(prefix="/demo", tags=["demo"])
COOKIE_NAME = "alphadesk_demo"


class DemoSessionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str = "DEMO_SYNTHETIC"
    expires_at: datetime
    guardian_halted: bool
    guardian_reason: str | None


async def _resolve(request: Request, token: str | None) -> DemoSessionRecord:
    if token is None:
        raise HTTPException(status_code=401, detail="Create a demo session first")
    try:
        return cast(DemoSessionRecord, await request.app.state.demo_sessions.resolve(token))
    except InvalidDemoSession as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@router.post("/session", response_model=DemoSessionStatus)
async def create_demo_session(request: Request, response: Response) -> DemoSessionStatus:
    record, token = await request.app.state.demo_sessions.create()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=24 * 60 * 60,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )
    return DemoSessionStatus(
        expires_at=record.expires_at,
        guardian_halted=record.guardian_halted,
        guardian_reason=record.guardian_reason,
    )


@router.get("/session", response_model=DemoSessionStatus)
async def demo_session_status(
    request: Request, alphadesk_demo: str | None = Cookie(default=None)
) -> DemoSessionStatus:
    record = await _resolve(request, alphadesk_demo)
    return DemoSessionStatus(
        expires_at=record.expires_at,
        guardian_halted=record.guardian_halted,
        guardian_reason=record.guardian_reason,
    )


@router.get("/workflow/replays/{scenario}", response_model=CatalystReplay)
async def catalyst_replay(scenario: ReplayScenario) -> CatalystReplay:
    return run_catalyst_replay(scenario)


@router.post("/guardian/halt", response_model=DemoSessionStatus)
async def demo_halt(
    request: Request, alphadesk_demo: str | None = Cookie(default=None)
) -> DemoSessionStatus:
    record = await _resolve(request, alphadesk_demo)
    async with request.app.state.database.sessions.begin() as session:
        attached = await session.get(type(record), record.demo_session_id, with_for_update=True)
        assert attached is not None
        attached.guardian_halted = True
        attached.guardian_reason = "Synthetic manual kill-switch scenario."
        attached.updated_at = datetime.now(UTC)
    return DemoSessionStatus(
        expires_at=record.expires_at,
        guardian_halted=True,
        guardian_reason="Synthetic manual kill-switch scenario.",
    )


@router.post("/guardian/recover", response_model=DemoSessionStatus)
async def demo_recover(
    request: Request, alphadesk_demo: str | None = Cookie(default=None)
) -> DemoSessionStatus:
    record = await _resolve(request, alphadesk_demo)
    async with request.app.state.database.sessions.begin() as session:
        attached = await session.get(type(record), record.demo_session_id, with_for_update=True)
        assert attached is not None
        attached.guardian_halted = False
        attached.guardian_reason = None
        attached.updated_at = datetime.now(UTC)
    return DemoSessionStatus(
        expires_at=record.expires_at, guardian_halted=False, guardian_reason=None
    )
