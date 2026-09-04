from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.auth.registration import RegistrationService, RegistrationUnavailable
from packages.auth.supabase_admin import SupabaseRegistrationStatus

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterOperator(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    invitation_code: str = Field(min_length=20, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class RegistrationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str = "created"
    next: str = "sign_in"


class RegistrationStatusView(BaseModel):
    model_config = ConfigDict(frozen=True)

    supabase_url_configured: bool
    server_secret_configured: bool
    public_signup_disabled: bool
    admin_auth_reachable: bool
    registration_available: bool


def _status_view(value: SupabaseRegistrationStatus) -> RegistrationStatusView:
    return RegistrationStatusView(
        supabase_url_configured=value.supabase_url_configured,
        server_secret_configured=value.server_secret_configured,
        public_signup_disabled=value.public_signup_disabled,
        admin_auth_reachable=value.admin_auth_reachable,
        registration_available=value.registration_available,
    )


@router.get("/registration-status", response_model=RegistrationStatusView)
async def registration_status(request: Request) -> RegistrationStatusView:
    adapter = request.app.state.supabase_admin
    if adapter is None:
        return _status_view(
            SupabaseRegistrationStatus(
                supabase_url_configured=bool(request.app.state.settings.supabase_url),
                server_secret_configured=False,
                public_signup_disabled=False,
                admin_auth_reachable=False,
            )
        )
    return _status_view(await adapter.registration_status())


@router.post(
    "/register",
    response_model=RegistrationResult,
    status_code=status.HTTP_201_CREATED,
)
async def register_operator(payload: RegisterOperator, request: Request) -> RegistrationResult:
    database = request.app.state.database
    adapter = request.app.state.supabase_admin
    if database is None or adapter is None:
        raise HTTPException(status_code=503, detail="Connected registration is unavailable")
    provider_status = await adapter.registration_status()
    if not provider_status.registration_available:
        raise HTTPException(status_code=503, detail="Connected registration is unavailable")
    try:
        await RegistrationService(
            database.sessions,
            adapter,
            request.app.state.settings.admin_emails,
        ).register(payload.email, payload.password, payload.invitation_code)
    except RegistrationUnavailable as error:
        raise HTTPException(
            status_code=409, detail="Registration could not be completed"
        ) from error
    return RegistrationResult()
