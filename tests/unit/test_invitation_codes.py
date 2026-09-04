from __future__ import annotations

import re

from packages.auth.invitations import (
    generate_invitation_code,
    hash_invitation_token,
    invitation_hash_candidates,
    normalize_readable_code,
)


def test_readable_invitation_code_is_secure_and_normalized() -> None:
    code = generate_invitation_code()
    assert re.fullmatch(
        r"[0-9A-HJKMNP-TV-Z]{5}(?:-[0-9A-HJKMNP-TV-Z]{5}){4}-[0-9A-HJKMNP-TV-Z]", code
    )
    normalized = normalize_readable_code(code)
    assert len(normalized) == 26
    assert hash_invitation_token(normalized) in invitation_hash_candidates(code.lower())
    assert hash_invitation_token(normalized) in invitation_hash_candidates(code.replace("-", " "))


def test_legacy_invitation_tokens_remain_case_sensitive() -> None:
    legacy = "AbCdEf_-legacy-token-that-is-long-enough-1234"
    assert hash_invitation_token(legacy) in invitation_hash_candidates(legacy)
