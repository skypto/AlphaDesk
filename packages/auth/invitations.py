from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.database.models import (
    InvitationRecord,
)

DEFAULT_WATCHLIST = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "SPY", "TSLA")
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
READABLE_CODE_LENGTH = 26


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_readable_code(code: str) -> str:
    return "".join(character for character in code.upper() if character not in {"-", " "})


def invitation_hash_candidates(code: str) -> tuple[str, ...]:
    raw = code.strip()
    normalized = normalize_readable_code(raw)
    hashes = [hash_invitation_token(normalized)]
    legacy_hash = hash_invitation_token(raw)
    if legacy_hash not in hashes:
        hashes.append(legacy_hash)
    return tuple(hashes)


def generate_invitation_code() -> str:
    raw = "".join(secrets.choice(CROCKFORD_ALPHABET) for _ in range(READABLE_CODE_LENGTH))
    return "-".join(raw[index : index + 5] for index in range(0, len(raw), 5))


class InvitationUnavailable(RuntimeError):
    pass


class InvitationService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(
        self,
        *,
        created_by_user_id: UUID,
        comment: str,
        max_uses: int = 1,
        expires_at: datetime | None = None,
    ) -> tuple[InvitationRecord, str]:
        raw_token = generate_invitation_code()
        normalized_token = normalize_readable_code(raw_token)
        now = datetime.now(UTC)
        record = InvitationRecord(
            invitation_id=uuid4(),
            token_hash=hash_invitation_token(normalized_token),
            code_format="crockford_v1",
            comment=comment,
            max_uses=max_uses,
            use_count=0,
            expires_at=expires_at or now + timedelta(days=7),
            disabled_at=None,
            created_by_user_id=created_by_user_id,
            created_at=now,
        )
        async with self._sessions.begin() as session:
            session.add(record)
        return record, raw_token

    @staticmethod
    def available(record: InvitationRecord, now: datetime | None = None) -> bool:
        checked_at = now or datetime.now(UTC)
        return (
            record.disabled_at is None
            and (record.expires_at is None or record.expires_at > checked_at)
            and record.use_count < record.max_uses
        )

    async def inspect(self, token: str) -> InvitationRecord | None:
        async with self._sessions() as session:
            return cast(
                InvitationRecord | None,
                await session.scalar(
                    select(InvitationRecord).where(
                        InvitationRecord.token_hash.in_(invitation_hash_candidates(token))
                    )
                ),
            )
