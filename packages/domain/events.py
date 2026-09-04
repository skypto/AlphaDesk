from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID | None = None
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    available_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str
    schema_version: int = 1
    correlation_id: UUID
    causation_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
