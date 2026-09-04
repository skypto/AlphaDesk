from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.database.models import AuditRecord, WorkspaceCredentialRecord
from packages.security.credentials import CredentialCipher


class CredentialStore:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], cipher: CredentialCipher
    ) -> None:
        self._sessions = sessions
        self._cipher = cipher

    async def save(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        provider: str,
        secret_payload: dict[str, Any],
        configuration: dict[str, Any],
        validation_status: str,
        enabled: bool,
    ) -> WorkspaceCredentialRecord:
        now = datetime.now(UTC)
        encrypted = self._cipher.encrypt(workspace_id, provider, secret_payload)
        values = {
            "credential_id": uuid4(),
            "workspace_id": workspace_id,
            "provider": provider,
            "key_version": encrypted.key_version,
            "nonce": encrypted.nonce,
            "ciphertext": encrypted.ciphertext,
            "fingerprint": encrypted.fingerprint,
            "configuration": configuration,
            "validation_status": validation_status,
            "enabled": enabled,
            "validated_at": now if validation_status == "VERIFIED" else None,
            "created_at": now,
            "updated_at": now,
        }
        statement = (
            insert(WorkspaceCredentialRecord)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_workspace_credential_provider",
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"credential_id", "created_at"}
                },
            )
            .returning(WorkspaceCredentialRecord)
        )
        async with self._sessions.begin() as session:
            record = (await session.scalars(statement)).one()
            session.add(
                AuditRecord(
                    audit_id=uuid4(),
                    workspace_id=workspace_id,
                    actor_user_id=actor_user_id,
                    action=f"credential.{provider.lower()}.saved",
                    detail={"fingerprint": encrypted.fingerprint, "status": validation_status},
                    occurred_at=now,
                )
            )
            return record

    async def get(self, workspace_id: UUID, provider: str) -> WorkspaceCredentialRecord | None:
        async with self._sessions() as session:
            return cast(
                WorkspaceCredentialRecord | None,
                await session.scalar(
                    select(WorkspaceCredentialRecord).where(
                        WorkspaceCredentialRecord.workspace_id == workspace_id,
                        WorkspaceCredentialRecord.provider == provider,
                    )
                ),
            )

    async def reveal(self, workspace_id: UUID, provider: str) -> dict[str, Any] | None:
        record = await self.get(workspace_id, provider)
        if record is None:
            return None
        return self._cipher.decrypt(
            workspace_id,
            provider,
            record.key_version,
            record.nonce,
            record.ciphertext,
        )

    async def delete(self, *, workspace_id: UUID, actor_user_id: UUID, provider: str) -> None:
        now = datetime.now(UTC)
        async with self._sessions.begin() as session:
            await session.execute(
                delete(WorkspaceCredentialRecord).where(
                    WorkspaceCredentialRecord.workspace_id == workspace_id,
                    WorkspaceCredentialRecord.provider == provider,
                )
            )
            session.add(
                AuditRecord(
                    audit_id=uuid4(),
                    workspace_id=workspace_id,
                    actor_user_id=actor_user_id,
                    action=f"credential.{provider.lower()}.deleted",
                    detail={},
                    occurred_at=now,
                )
            )
