from __future__ import annotations

from fastapi import APIRouter, Request

from packages.domain.system import BrokerState, SystemStatus

router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=SystemStatus)
async def system_status(request: Request) -> SystemStatus:
    settings = request.app.state.settings
    return SystemStatus(
        mode=settings.mode,
        environment=settings.environment,
        broker_state=BrokerState.NOT_CONFIGURED,
        autonomous_execution_enabled=False,
        guardian_halted=True,
        guardian_reason="Connected broker state is private and requires authentication.",
    )
