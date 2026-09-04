from __future__ import annotations

from typing import Any
from uuid import UUID

import nats
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext
from nats.js.errors import NotFoundError


class JetStreamEventBus:
    stream_name = "ALPHADESK_EVENTS"
    subject_pattern = "alphadesk.events.>"

    def __init__(self, url: str, client_name: str) -> None:
        self.url = url
        self.client_name = client_name
        self._client: NATSClient | None = None
        self._jetstream: JetStreamContext | None = None

    async def connect(self) -> None:
        self._client = await nats.connect(
            servers=[self.url],
            name=self.client_name,
            connect_timeout=5,
            max_reconnect_attempts=10,
        )
        self._jetstream = self._client.jetstream()

    async def ensure_stream(self) -> None:
        jetstream = self._require_jetstream()
        try:
            await jetstream.stream_info(self.stream_name)
        except NotFoundError:
            await jetstream.add_stream(
                name=self.stream_name,
                subjects=[self.subject_pattern],
            )

    async def publish(self, subject: str, payload: bytes) -> Any:
        if not subject.startswith("alphadesk.events."):
            raise ValueError("AlphaDesk event subjects must start with 'alphadesk.events.'.")
        return await self._require_jetstream().publish(subject, payload)

    @staticmethod
    def workspace_subject(workspace_id: UUID, event_type: str) -> str:
        normalized = event_type.lower().replace("_", "-").replace(".", "-")
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
        if not normalized or any(character not in allowed for character in normalized):
            raise ValueError("Event type contains unsupported subject characters")
        return f"alphadesk.events.workspace.{workspace_id}.{normalized}"

    async def publish_workspace(
        self, workspace_id: UUID, event_type: str, payload: bytes
    ) -> Any:
        return await self.publish(self.workspace_subject(workspace_id, event_type), payload)

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.drain()
        self._client = None
        self._jetstream = None

    def _require_jetstream(self) -> JetStreamContext:
        if self._jetstream is None:
            raise RuntimeError("JetStream client is not connected.")
        return self._jetstream
