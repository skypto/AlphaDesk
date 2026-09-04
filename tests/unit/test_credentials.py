from __future__ import annotations

import base64
from uuid import UUID

import pytest
from cryptography.exceptions import InvalidTag

from packages.security.credentials import CredentialCipher, CredentialConfigurationError

WORKSPACE = UUID("10000000-0000-0000-0000-000000000001")


def key(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def test_credentials_round_trip_without_plaintext_ciphertext() -> None:
    cipher = CredentialCipher(f"v1:{key(b'a' * 32)}")
    encrypted = cipher.encrypt(
        WORKSPACE,
        "ALPACA",
        {"api_key_id": "paper-key", "secret_key": "paper-secret"},
    )

    assert b"paper-key" not in encrypted.ciphertext
    assert b"paper-secret" not in encrypted.ciphertext
    assert cipher.decrypt(
        WORKSPACE,
        "ALPACA",
        encrypted.key_version,
        encrypted.nonce,
        encrypted.ciphertext,
    ) == {"api_key_id": "paper-key", "secret_key": "paper-secret"}


def test_workspace_and_provider_are_authenticated_encryption_context() -> None:
    cipher = CredentialCipher(f"v1:{key(b'a' * 32)}")
    encrypted = cipher.encrypt(WORKSPACE, "ALPACA", {"secret": "value"})

    with pytest.raises(InvalidTag):
        cipher.decrypt(
            UUID("20000000-0000-0000-0000-000000000002"),
            "ALPACA",
            encrypted.key_version,
            encrypted.nonce,
            encrypted.ciphertext,
        )


def test_master_key_must_be_exactly_32_bytes() -> None:
    with pytest.raises(CredentialConfigurationError, match="32 bytes"):
        CredentialCipher(f"v1:{key(b'too-short')}")
