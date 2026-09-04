from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.app import create_app
from packages.auth.supabase_admin import SupabaseRegistrationStatus
from packages.configuration.settings import Settings


class FakeSupabaseAdmin:
    async def registration_status(self) -> SupabaseRegistrationStatus:
        return SupabaseRegistrationStatus(
            supabase_url_configured=True,
            server_secret_configured=True,
            public_signup_disabled=True,
            admin_auth_reachable=True,
        )


def test_registration_status_exposes_no_secrets() -> None:
    app = create_app(
        Settings(
            infrastructure_checks=False,
            supabase_url="https://project.supabase.co",
            supabase_secret_key="sb_secret_test-only-value",
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        app.state.supabase_admin = FakeSupabaseAdmin()
        response = client.get("/api/v1/auth/registration-status")

    assert response.status_code == 200
    assert response.json() == {
        "supabase_url_configured": True,
        "server_secret_configured": True,
        "public_signup_disabled": True,
        "admin_auth_reachable": True,
        "registration_available": True,
    }
    assert "sb_secret_test-only-value" not in response.text


def test_registration_fails_closed_without_infrastructure() -> None:
    app = create_app(Settings(infrastructure_checks=False, _env_file=None))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "operator@example.test",
                "password": "strong-password",
                "invitation_code": "ABCDE-FGHJK-MNPQR-STVWX-YZ234-A",
            },
        )
        assert client.get("/api/v1/invitations/not-a-code").status_code == 404
        assert (
            client.post("/api/v1/invitations/redeem", json={"token": "x" * 24}).status_code == 404
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Connected registration is unavailable"}


def test_admin_workspace_provisioning_requires_authentication() -> None:
    app = create_app(Settings(infrastructure_checks=False, _env_file=None))
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/workspace")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
