from __future__ import annotations

from uuid import uuid4

from packages.domain.events import EventEnvelope


def test_event_envelope_has_required_audit_identity() -> None:
    aggregate_id = uuid4()
    correlation_id = uuid4()
    event = EventEnvelope(
        event_type="SYSTEM_STARTED",
        aggregate_type="system",
        aggregate_id=aggregate_id,
        source="test",
        correlation_id=correlation_id,
    )

    assert event.aggregate_id == aggregate_id
    assert event.correlation_id == correlation_id
    assert event.occurred_at.tzinfo is not None
    assert event.available_at.tzinfo is not None
    assert event.schema_version == 1
