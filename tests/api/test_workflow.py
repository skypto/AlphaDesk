from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.app import create_app
from packages.configuration.settings import Settings


@pytest.mark.parametrize(
    ("scenario", "disposition", "last_event"),
    [
        ("approved", "ORDER_INTENT_CREATED", "ORDER_INTENT_CREATED"),
        ("no_trade", "NO_TRADE", "NO_TRADE_DECISION"),
        ("risk_veto", "RISK_REJECTED", "RISK_REJECTED"),
        ("partial_fill", "ORDER_PARTIALLY_FILLED", "ORDER_PARTIALLY_FILLED"),
        ("submission_uncertain", "SUBMISSION_UNCERTAIN", "BROKER_RECONCILIATION_STARTED"),
        ("guardian_recovery", "RECOVERY_RECONCILED", "BROKER_RECONCILIATION_COMPLETED"),
    ],
)
def test_replay_scenarios_are_deterministic(
    scenario: str, disposition: str, last_event: str
) -> None:
    app = create_app(Settings(infrastructure_checks=False))
    with TestClient(app) as client:
        first = client.get(f"/api/v1/demo/workflow/replays/{scenario}").json()
        second = client.get(f"/api/v1/demo/workflow/replays/{scenario}").json()

    assert first == second
    assert first["disposition"] == disposition
    assert first["audit_timeline"][-1] == last_event
    if scenario in {"no_trade", "risk_veto"}:
        assert first["order_intent"] is None
