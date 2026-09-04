from __future__ import annotations

from packages.guardian.store import GuardianStore


class GuardianExecutionGate:
    def __init__(self, store: GuardianStore) -> None:
        self._store = store

    async def execution_allowed(self) -> tuple[bool, str]:
        status = await self._store.status()
        if not status.execution_allowed:
            reason = (
                status.active_incident.reason
                if status.active_incident is not None
                else "Guardian is halted"
            )
            return False, reason
        return True, "Guardian is normal"
