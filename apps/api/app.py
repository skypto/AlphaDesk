from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.admin import router as admin_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.demo import router as demo_router
from apps.api.routes.desk import router as desk_router
from apps.api.routes.health import router as health_router
from apps.api.routes.identity import router as identity_router
from apps.api.routes.system import router as system_router
from packages.auth.jwt import SupabaseJWTVerifier
from packages.auth.supabase_admin import SupabaseAdminAuth
from packages.configuration.settings import Settings, get_settings
from packages.database.session import Database
from packages.demo.sessions import DemoSessionService, ephemeral_demo_key
from packages.event_bus.client import JetStreamEventBus
from packages.observability.logging import configure_logging, get_logger
from packages.security.credentials import CredentialCipher, CredentialConfigurationError

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(resolved_settings.log_level)
        app.state.settings = resolved_settings
        app.state.readiness = {
            "configuration": "healthy",
            "database": "disabled",
            "event_bus": "disabled",
        }
        app.state.database = None
        app.state.event_bus = None
        app.state.auth_verifier = None
        app.state.supabase_admin = None
        app.state.credential_cipher = None
        app.state.demo_sessions = None

        if resolved_settings.infrastructure_checks:
            database = Database(resolved_settings.database_url)
            await database.ping()
            app.state.database = database
            app.state.readiness["database"] = "healthy"

            event_bus = JetStreamEventBus(resolved_settings.nats_url, client_name="alphadesk-api")
            await event_bus.connect()
            await event_bus.ensure_stream()
            app.state.event_bus = event_bus
            app.state.readiness["event_bus"] = "healthy"

            signing_key = (
                ephemeral_demo_key()
                if resolved_settings.demo_session_signing_key is None
                else resolved_settings.demo_session_signing_key.get_secret_value().encode()
            )
            app.state.demo_sessions = DemoSessionService(database.sessions, signing_key)

        if resolved_settings.supabase_url:
            app.state.auth_verifier = SupabaseJWTVerifier(
                resolved_settings.supabase_url,
                resolved_settings.supabase_jwt_audience,
            )
        if resolved_settings.supabase_url and resolved_settings.supabase_secret_key is not None:
            app.state.supabase_admin = SupabaseAdminAuth(
                resolved_settings.supabase_url,
                resolved_settings.supabase_secret_key.get_secret_value(),
            )
        if resolved_settings.credential_master_keys is not None:
            try:
                app.state.credential_cipher = CredentialCipher(
                    resolved_settings.credential_master_keys.get_secret_value()
                )
            except CredentialConfigurationError:
                app.state.readiness["credential_encryption"] = "unhealthy"

        logger.info(
            "api_started",
            extra={
                "event": "api_started",
                "mode": resolved_settings.mode.value,
                "environment": resolved_settings.environment,
            },
        )
        try:
            yield
        finally:
            event_bus = app.state.event_bus
            if event_bus is not None:
                await event_bus.close()
            database = app.state.database
            if database is not None:
                await database.close()
            logger.info("api_stopped", extra={"event": "api_stopped"})

    application = FastAPI(
        title="AlphaDesk API",
        version="0.1.0",
        description="Paper-only autonomous options research and execution desk.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["DELETE", "GET", "POST", "PUT"],
        allow_headers=["Accept", "Authorization", "Content-Type"],
        allow_credentials=True,
    )
    application.state.settings = resolved_settings
    application.state.readiness = {"configuration": "healthy"}
    application.state.auth_verifier = None
    application.state.supabase_admin = None
    application.state.credential_cipher = None
    application.state.demo_sessions = None
    application.include_router(health_router)
    application.include_router(system_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(demo_router, prefix="/api/v1")
    application.include_router(identity_router, prefix="/api/v1")
    application.include_router(admin_router, prefix="/api/v1")
    application.include_router(desk_router, prefix="/api/v1")
    return application


app = create_app()
