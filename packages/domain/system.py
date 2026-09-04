from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from packages.configuration.settings import SystemMode


class BrokerState(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    RECONCILED = "RECONCILED"
    DIVERGENT = "DIVERGENT"


class SystemStatus(BaseModel):
    mode: SystemMode
    environment: str
    broker_state: BrokerState
    autonomous_execution_enabled: bool
    guardian_halted: bool
    guardian_reason: str | None = None
