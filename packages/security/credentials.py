from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CredentialConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedCredential:
    key_version: str
    nonce: bytes
    ciphertext: bytes
    fingerprint: str


class CredentialCipher:
    """AES-GCM envelope with workspace/provider-bound associated data."""

    def __init__(self, encoded_keys: str) -> None:
        parsed: dict[str, bytes] = {}
        for item in encoded_keys.split(","):
            if not item.strip():
                continue
            try:
                version, encoded = item.strip().split(":", 1)
                key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            except Exception as error:
                raise CredentialConfigurationError(
                    "Credential master keys must use version:base64 format"
                ) from error
            if len(key) != 32:
                raise CredentialConfigurationError("Every credential master key must be 32 bytes")
            parsed[version] = key
        if not parsed:
            raise CredentialConfigurationError("At least one credential master key is required")
        self._keys = parsed
        self._active_version = list(parsed)[-1]

    @staticmethod
    def _aad(workspace_id: UUID, provider: str, key_version: str) -> bytes:
        return f"alphadesk:{workspace_id}:{provider}:{key_version}".encode()

    def encrypt(
        self, workspace_id: UUID, provider: str, payload: dict[str, Any]
    ) -> EncryptedCredential:
        version = self._active_version
        plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._keys[version]).encrypt(
            nonce, plaintext, self._aad(workspace_id, provider, version)
        )
        return EncryptedCredential(
            key_version=version,
            nonce=nonce,
            ciphertext=ciphertext,
            fingerprint=hashlib.sha256(plaintext).hexdigest()[:12],
        )

    def decrypt(
        self,
        workspace_id: UUID,
        provider: str,
        key_version: str,
        nonce: bytes,
        ciphertext: bytes,
    ) -> dict[str, Any]:
        key = self._keys.get(key_version)
        if key is None:
            raise CredentialConfigurationError(
                f"Credential key version {key_version} is unavailable"
            )
        plaintext = AESGCM(key).decrypt(
            nonce, ciphertext, self._aad(workspace_id, provider, key_version)
        )
        value = json.loads(plaintext)
        if not isinstance(value, dict):
            raise CredentialConfigurationError("Decrypted credential payload is invalid")
        return value
