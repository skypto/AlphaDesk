from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.auth.invitations import (
    InvitationService,
    InvitationUnavailable,
    invitation_hash_candidates,
)
from packages.auth.supabase_admin import SupabaseAdminAuth, SupabaseAdminError
from packages.auth.workspaces import create_connected_workspace
from packages.database.models import (
    AppUserRecord,
    InvitationRecord,
    InvitationRedemptionRecord,
    WorkspaceRecord,
)
from packages.observability.logging import get_logger

logger = get_logger(__name__)


class RegistrationUnavailable(RuntimeError):
    pass


class RegistrationService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        supabase: SupabaseAdminAuth,
        admin_emails: frozenset[str],
    ) -> None:
        self._sessions = sessions
        self._supabase = supabase
        self._admin_emails = admin_emails

    async def register(self, email: str, password: str, invitation_code: str) -> WorkspaceRecord:
        normalized_email = email.strip().lower()
        if normalized_email in self._admin_emails:
            raise RegistrationUnavailable("Registration could not be completed")

        created_subject: str | None = None
        try:
            async with self._sessions.begin() as session:
                invitation = await session.scalar(
                    select(InvitationRecord)
                    .where(
                        InvitationRecord.token_hash.in_(invitation_hash_candidates(invitation_code))
                    )
                    .with_for_update()
                )
                if invitation is None or not InvitationService.available(invitation):
                    raise RegistrationUnavailable("Registration could not be completed")
                existing = await session.scalar(
                    select(AppUserRecord).where(AppUserRecord.email == normalized_email)
                )
                if existing is not None:
                    raise RegistrationUnavailable("Registration could not be completed")

                try:
                    identity = await self._supabase.create_user(normalized_email, password)
                except SupabaseAdminError as error:
                    raise RegistrationUnavailable("Registration could not be completed") from error
                created_subject = identity.subject

                now = datetime.now(UTC)
                user = AppUserRecord(
                    user_id=uuid4(),
                    auth_subject=identity.subject,
                    email=identity.email,
                    is_admin=False,
                    created_at=now,
                    last_seen_at=now,
                )
                session.add(user)
                await session.flush()
                workspace = await create_connected_workspace(
                    session,
                    owner_user_id=user.user_id,
                    owner_email=user.email,
                    actor_user_id=user.user_id,
                    audit_action="INVITATION_CONNECTED_WORKSPACE_PROVISIONED",
                )
                session.add(
                    InvitationRedemptionRecord(
                        redemption_id=uuid4(),
                        invitation_id=invitation.invitation_id,
                        user_id=user.user_id,
                        redeemed_at=now,
                    )
                )
                invitation.use_count += 1
                return workspace
        except (InvitationUnavailable, RegistrationUnavailable):
            raise
        except Exception:
            if created_subject is not None:
                try:
                    await self._supabase.delete_user(created_subject)
                except SupabaseAdminError:
                    logger.critical(
                        "supabase_registration_cleanup_uncertain",
                        extra={
                            "event": "supabase_registration_cleanup_uncertain",
                            "auth_subject": created_subject,
                        },
                    )
            raise
