from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.database.models import DemoSessionRecord


class InvalidDemoSession(RuntimeError):
    pass


class DemoSessionService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        signing_key: bytes,
        *,
        lifetime: timedelta = timedelta(hours=24),
    ) -> None:
        if len(signing_key) < 32:
            raise ValueError("Demo session signing key must contain at least 32 bytes")
        self._sessions = sessions
        self._signing_key = signing_key
        self._lifetime = lifetime

    def _signature(self, value: str) -> str:
        digest = hmac.new(self._signing_key, value.encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    async def create(self) -> tuple[DemoSessionRecord, str]:
        now = datetime.now(UTC)
        record = DemoSessionRecord(
            demo_session_id=uuid4(),
            expires_at=now + self._lifetime,
            guardian_halted=False,
            guardian_reason=None,
            created_at=now,
            updated_at=now,
        )
        async with self._sessions.begin() as session:
            session.add(record)
        payload = f"{record.demo_session_id}.{int(record.expires_at.timestamp())}"
        return record, f"{payload}.{self._signature(payload)}"

    async def resolve(self, token: str) -> DemoSessionRecord:
        try:
            identifier, expires, signature = token.split(".", 2)
            session_id = UUID(identifier)
            expires_at = datetime.fromtimestamp(int(expires), tz=UTC)
        except (ValueError, TypeError) as error:
            raise InvalidDemoSession("Invalid demo session") from error
        payload = f"{identifier}.{expires}"
        if not hmac.compare_digest(signature, self._signature(payload)):
            raise InvalidDemoSession("Invalid demo session")
        if expires_at <= datetime.now(UTC):
            raise InvalidDemoSession("Demo session expired")
        async with self._sessions() as session:
            record = await session.get(DemoSessionRecord, session_id)
        if record is None or record.expires_at <= datetime.now(UTC):
            raise InvalidDemoSession("Demo session expired")
        return record


def ephemeral_demo_key() -> bytes:
    return secrets.token_bytes(32)
