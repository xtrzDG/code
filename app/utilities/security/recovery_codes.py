"""
Recovery codes: generation, normalization of what a person types, and
keyed hashing.

A code is three groups of four characters of an alphabet without
look-alikes (no i, l, o, 0 or 1): about 60 random bits, far beyond guessing
within the attempt limits, and too many to try offline even if the hashes
leaked. Only the hash is stored: an HMAC-SHA256 keyed with the code's id
and its user's id, so equal codes of two users hash differently, compared
in constant time. The key does not come from ENCRYPTION_KEY, so rotating
the key ring keeps every code working.
"""

import hmac
import re
import secrets
from hashlib import sha256

from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.mfa.prefixed_id import RecoveryCodeId
from app.schemas.typings.mfa.strings import RawRecoveryCodeInput, RecoveryCodeHash
from app.schemas.typings.users.prefixed_id import UserId

RECOVERY_CODE_ALPHABET: str = "abcdefghjkmnpqrstuvwxyz23456789"
RECOVERY_CODE_GROUPS: int = 3
RECOVERY_CODE_GROUP_LENGTH: int = 4
RECOVERY_CODES_PER_SET: int = 10
TYPED_SEPARATORS: re.Pattern[str] = re.compile(r"[\s\-_.]+")


def generate_recovery_code() -> RecoveryCode:
    groups: list[str] = [
        "".join(
            secrets.choice(RECOVERY_CODE_ALPHABET)
            for _ in range(RECOVERY_CODE_GROUP_LENGTH)
        )
        for _ in range(RECOVERY_CODE_GROUPS)
    ]
    return RecoveryCode("-".join(groups))


def generate_recovery_codes() -> list[RecoveryCode]:
    """A new set of distinct codes."""

    codes: list[RecoveryCode] = []
    while len(codes) < RECOVERY_CODES_PER_SET:
        code: RecoveryCode = generate_recovery_code()
        if code not in codes:
            codes.append(code)

    return codes


def normalize_recovery_code(typed: RawRecoveryCodeInput) -> RecoveryCode | None:
    """
    The code a person typed, in any case and with or without dashes or
    spaces; None when it cannot be a recovery code.
    """

    compact: str = TYPED_SEPARATORS.sub("", str(typed)).lower()
    expected_length: int = RECOVERY_CODE_GROUPS * RECOVERY_CODE_GROUP_LENGTH
    if len(compact) != expected_length or any(
        character not in RECOVERY_CODE_ALPHABET for character in compact
    ):
        return None

    groups: list[str] = [
        compact[start : start + RECOVERY_CODE_GROUP_LENGTH]
        for start in range(0, expected_length, RECOVERY_CODE_GROUP_LENGTH)
    ]
    return RecoveryCode("-".join(groups))


def hash_recovery_code(
    user_id: UserId, code_id: RecoveryCodeId, code: RecoveryCode
) -> RecoveryCodeHash:
    key: bytes = f"{user_id}/{code_id}".encode()
    digest: str = hmac.new(key, str(code).encode(), sha256).hexdigest()
    return RecoveryCodeHash(digest)


def is_recovery_code_matching(
    user_id: UserId,
    code_id: RecoveryCodeId,
    code: RecoveryCode,
    code_hash: RecoveryCodeHash,
) -> bool:
    candidate: RecoveryCodeHash = hash_recovery_code(user_id, code_id, code)
    return hmac.compare_digest(str(candidate).encode(), str(code_hash).encode())
