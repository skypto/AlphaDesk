from __future__ import annotations

from uuid import UUID

import pytest

from packages.event_bus.client import JetStreamEventBus


@pytest.mark.asyncio
async def test_publish_requires_alphadesk_subject_namespace() -> None:
    event_bus = JetStreamEventBus("nats://unused:4222", "test")
    with pytest.raises(ValueError, match="must start"):
        await event_bus.publish("orders.created", b"{}")


def test_connected_subjects_are_namespaced_by_workspace() -> None:
    first = UUID("10000000-0000-0000-0000-000000000001")
    second = UUID("20000000-0000-0000-0000-000000000002")
    assert JetStreamEventBus.workspace_subject(first, "order.created.v1") == (
        "alphadesk.events.workspace.10000000-0000-0000-0000-000000000001.order-created-v1"
    )
    assert JetStreamEventBus.workspace_subject(first, "order.created.v1") != (
        JetStreamEventBus.workspace_subject(second, "order.created.v1")
    )
