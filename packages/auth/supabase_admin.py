from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SupabaseAdminError(RuntimeError):
    """A redacted Supabase Admin API failure safe to surface internally."""


@dataclass(frozen=True)
class SupabaseIdentity:
    subject: str
    email: str


@dataclass(frozen=True)
class SupabaseRegistrationStatus:
    supabase_url_configured: bool
    server_secret_configured: bool
    public_signup_disabled: bool
    admin_auth_reachable: bool

    @property
    def registration_available(self) -> bool:
        return all(
            (
                self.supabase_url_configured,
                self.server_secret_configured,
                self.public_signup_disabled,
                self.admin_auth_reachable,
            )
        )


class SupabaseAdminAuth:
    """Minimal server-only adapter for hosted Supabase Auth administration."""

    def __init__(self, supabase_url: str, secret_key: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = f"{supabase_url.rstrip('/')}/auth/v1"
        self._secret_key = secret_key
        self._timeout_seconds = timeout_seconds

    def _request_sync(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "apikey": self._secret_key,
                "Authorization": f"Bearer {self._secret_key}",
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                document = json.loads(response.read().decode() or "{}")
                if not isinstance(document, dict):
                    raise SupabaseAdminError("Supabase Auth returned an invalid response")
                return document
        except HTTPError as error:
            if error.code in {400, 409, 422}:
                raise SupabaseAdminError("Supabase could not create this account") from error
            raise SupabaseAdminError("Supabase Auth administration is unavailable") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise SupabaseAdminError("Supabase Auth administration is unavailable") from error

    async def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._request_sync, method, path, payload)

    async def create_user(self, email: str, password: str) -> SupabaseIdentity:
        document = await self._request(
            "POST",
            "/admin/users",
            {"email": email, "password": password, "email_confirm": True},
        )
        subject = str(document.get("id", "")).strip()
        returned_email = str(document.get("email", "")).strip().lower()
        if not subject or returned_email != email:
            raise SupabaseAdminError("Supabase Auth returned an invalid user record")
        return SupabaseIdentity(subject=subject, email=returned_email)

    async def delete_user(self, subject: str) -> None:
        await self._request("DELETE", f"/admin/users/{subject}")

    async def registration_status(self) -> SupabaseRegistrationStatus:
        public_signup_disabled = False
        admin_auth_reachable = False
        try:
            settings = await self._request("GET", "/settings")
            public_signup_disabled = settings.get("disable_signup") is True
            await self._request("GET", "/admin/users?page=1&per_page=1")
            admin_auth_reachable = True
        except SupabaseAdminError:
            pass
        return SupabaseRegistrationStatus(
            supabase_url_configured=True,
            server_secret_configured=True,
            public_signup_disabled=public_signup_disabled,
            admin_auth_reachable=admin_auth_reachable,
        )
