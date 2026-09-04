from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.database.models import AIWorkflowRunRecord
from packages.domain.ai import AIWorkflowResult


class AIWorkflowStore:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], workspace_id: UUID | None = None
    ) -> None:
        self._sessions = sessions
        self._workspace_id = workspace_id

    async def save(
        self,
        *,
        correlation_id: UUID,
        input_payload: dict[str, object],
        result: AIWorkflowResult,
    ) -> UUID:
        run_id = uuid4()
        async with self._sessions.begin() as session:
            session.add(
                AIWorkflowRunRecord(
                    run_id=run_id,
                    workspace_id=self._workspace_id,
                    correlation_id=correlation_id,
                    provider=result.provider,
                    model=result.model,
                    prompt_versions=result.prompt_versions,
                    schema_version=result.schema_version,
                    input_payload=input_payload,
                    output_payload=result.model_dump(mode="json"),
                    degraded=result.degraded,
                    failure_reason=result.failure_reason,
                    created_at=datetime.now(UTC),
                )
            )
        return run_id
