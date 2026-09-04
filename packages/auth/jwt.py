from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient


class AuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    subject: str
    email: str


class SupabaseJWTVerifier:
    """Caches Supabase's JWKS and validates issuer, audience, signature, and expiry."""

    def __init__(self, supabase_url: str, audience: str = "authenticated") -> None:
        base = supabase_url.rstrip("/")
        self._issuer = f"{base}/auth/v1"
        self._audience = audience
        self._jwks = PyJWKClient(f"{self._issuer}/.well-known/jwks.json", cache_keys=True)

    def _verify_sync(self, token: str) -> VerifiedIdentity:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud"]},
            )
        except Exception as error:
            raise AuthenticationError("Invalid or expired access token") from error
        subject = str(claims.get("sub", ""))
        email = str(claims.get("email", "")).strip().lower()
        if not subject or not email:
            raise AuthenticationError("Authenticated identity is missing subject or email")
        return VerifiedIdentity(subject=subject, email=email)

    async def verify(self, token: str) -> VerifiedIdentity:
        return await asyncio.to_thread(self._verify_sync, token)
