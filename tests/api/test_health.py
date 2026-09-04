from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.app import create_app
from packages.configuration.settings import Settings


def test_health_and_system_status_are_safe_without_broker_credentials() -> None:
    settings = Settings(infrastructure_checks=False, _env_file=None)
    with TestClient(create_app(settings)) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        system = client.get("/api/v1/system/status")

    assert live.status_code == 200
    assert live.json() == {"status": "alive", "service": "api"}
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert system.status_code == 200
    assert system.json() == {
        "mode": "PAPER_ONLY",
        "environment": "development",
        "broker_state": "NOT_CONFIGURED",
        "autonomous_execution_enabled": False,
        "guardian_halted": True,
        "guardian_reason": "Connected broker state is private and requires authentication.",
    }


def test_global_broker_routes_are_removed_and_desk_routes_require_authentication() -> None:
    settings = Settings(infrastructure_checks=False, _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/broker/account").status_code == 404
        assert client.get("/api/v1/broker/positions").status_code == 404
        assert client.get("/api/v1/desk/broker/account").status_code == 401
        assert client.post("/api/v1/desk/guardian/halt").status_code == 401
