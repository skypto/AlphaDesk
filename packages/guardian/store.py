from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.database.models import GuardianIncidentRecord
from packages.domain.guardian import (
    GuardianIncident,
    GuardianState,
    GuardianStatus,
    GuardianTrigger,
)


class GuardianStore(Protocol):
    async def status(self) -> GuardianStatus: ...

    async def halt(
        self, triggers: tuple[GuardianTrigger, ...], reason: str
    ) -> GuardianIncident: ...

    async def recover(self, *, broker_state_known: bool) -> GuardianStatus: ...


class MemoryGuardianStore:
    def __init__(self) -> None:
        self.incident: GuardianIncident | None = None

    async def status(self) -> GuardianStatus:
        state = self.incident.state if self.incident is not None else GuardianState.NORMAL
        return GuardianStatus(
            state=state,
            active_incident=self.incident,
            execution_allowed=self.incident is None,
        )

    async def halt(self, triggers: tuple[GuardianTrigger, ...], reason: str) -> GuardianIncident:
        if self.incident is None:
            self.incident = GuardianIncident(
                state=GuardianState.HALTED, triggers=triggers, reason=reason
            )
        return self.incident

    async def recover(self, *, broker_state_known: bool) -> GuardianStatus:
        if not broker_state_known:
            raise RuntimeError("Guardian recovery requires known reconciled broker state")
        self.incident = None
        return await self.status()


class PostgresGuardianStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], workspace_id: UUID) -> None:
        self._sessions = sessions
        self._workspace_id = workspace_id

    async def _active(self, session: AsyncSession) -> GuardianIncidentRecord | None:
        return cast(
            GuardianIncidentRecord | None,
            await session.scalar(
                select(GuardianIncidentRecord)
                .where(
                    GuardianIncidentRecord.workspace_id == self._workspace_id,
                    GuardianIncidentRecord.cleared_at.is_(None),
                )
                .order_by(GuardianIncidentRecord.activated_at.desc())
                .limit(1)
            ),
        )

    @staticmethod
    def _domain(record: GuardianIncidentRecord) -> GuardianIncident:
        return GuardianIncident(
            incident_id=record.incident_id,
            state=GuardianState(record.state),
            triggers=tuple(GuardianTrigger(item) for item in record.triggers),
            reason=record.reason,
            activated_at=record.activated_at,
            cleared_at=record.cleared_at,
        )

    async def status(self) -> GuardianStatus:
        async with self._sessions() as session:
            record = await self._active(session)
            incident = None if record is None else self._domain(record)
            return GuardianStatus(
                state=GuardianState.NORMAL if incident is None else incident.state,
                active_incident=incident,
                execution_allowed=incident is None,
            )

    async def halt(self, triggers: tuple[GuardianTrigger, ...], reason: str) -> GuardianIncident:
        async with self._sessions.begin() as session:
            existing = await self._active(session)
            if existing is not None:
                return self._domain(existing)
            incident = GuardianIncident(
                state=GuardianState.HALTED, triggers=triggers, reason=reason
            )
            session.add(
                GuardianIncidentRecord(
                    incident_id=incident.incident_id,
                    workspace_id=self._workspace_id,
                    state=incident.state.value,
                    triggers=[item.value for item in incident.triggers],
                    reason=incident.reason,
                    activated_at=incident.activated_at,
                    cleared_at=None,
                )
            )
            return incident

    async def recover(self, *, broker_state_known: bool) -> GuardianStatus:
        if not broker_state_known:
            raise RuntimeError("Guardian recovery requires known reconciled broker state")
        async with self._sessions.begin() as session:
            await session.execute(
                update(GuardianIncidentRecord)
                .where(
                    GuardianIncidentRecord.workspace_id == self._workspace_id,
                    GuardianIncidentRecord.cleared_at.is_(None),
                )
                .values(state=GuardianState.NORMAL.value, cleared_at=datetime.now(UTC))
            )
        return await self.status()
