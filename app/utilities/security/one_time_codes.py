"""
One-time login codes: generation and keyed hashing.

Only the hash of a code is stored: an HMAC-SHA256 of the challenge id and
the code under a key derived from the platform key ring (ENCRYPTION_KEYS,
with its own label), so a copy of the database alone cannot test the
million codes of a challenge offline, the same code in two challenges
gives different hashes, and codes are compared in constant time. A code is
checked against every key of the ring, so a key rotation does not void the
codes of the last minutes. Without a key (development) a fixed text keys
it.

Challenges written before the hash was keyed (version 2 and older, without
`is_code_hash_server_keyed`) were keyed with their own id alone; they are
read that way until they expire (OTP_LIFETIME_SECONDS). A code issued by a
release of one kind and checked by the other during a rolling deploy may
fail: the person asks for a new one.
"""

import hashlib
import hmac
import secrets
from collections.abc import Sequence

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import OtpCodeHash
from app.utilities.security.key_ring import key_ring

OTP_CODE_DIGITS: int = 6
KEY_LABEL: bytes = b"assistant-workshop/login-codes/v1"
DEVELOPMENT_KEY_TEXT: str = "assistant-workshop development login-code key"
HASH_VERSION: str = "v2"


def generate_otp_code() -> OtpCode:
    """Return a uniformly random six-digit code from the OS CSPRNG."""

    random_number: int = secrets.randbelow(10**OTP_CODE_DIGITS)
    return OtpCode(f"{random_number:0{OTP_CODE_DIGITS}d}")


def derive_otp_hash_key(encryption_key: PlatformSecret | None) -> bytes:
    """The HMAC key of login code hashes under one key of the ring."""

    source: str = (
        str(encryption_key).strip()
        if encryption_key is not None and str(encryption_key).strip()
        else DEVELOPMENT_KEY_TEXT
    )
    return hmac.new(source.encode("utf-8"), KEY_LABEL, hashlib.sha256).digest()


def otp_hash_keys(settings: AppSettings) -> list[bytes]:
    """Every key a stored hash may be keyed with, the current (hashing) one first."""

    ring: list[PlatformSecret] = key_ring(settings)
    if not ring:
        return [derive_otp_hash_key(None)]

    return [derive_otp_hash_key(key) for key in ring]


def hash_otp_code(key: bytes, challenge_id: OtpChallengeId, code: OtpCode) -> OtpCodeHash:
    """The hex HMAC-SHA256 of a code and its challenge under a server key."""

    message: str = f"{HASH_VERSION}|{challenge_id}|{code}"
    digest: str = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    return OtpCodeHash(digest)


def hash_otp_code_by_challenge(challenge_id: OtpChallengeId, code: OtpCode) -> str:
    """
    How challenges of version 2 and older were hashed (keyed with the
    challenge id alone); a plain `str`, never stored again.
    """

    return hmac.new(
        key=str(challenge_id).encode("utf-8"),
        msg=str(code).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def is_otp_code_matching(
    challenge: OtpChallengeDocument,
    code: OtpCode,
    keys: Sequence[bytes],
) -> bool:
    """Compare a typed code with the challenge's stored hash in constant time."""

    stored: bytes = str(challenge.code_hash).encode("utf-8")
    candidates: list[str] = (
        [str(hash_otp_code(key, challenge.id, code)) for key in keys]
        if challenge.is_code_hash_server_keyed
        else [hash_otp_code_by_challenge(challenge.id, code)]
    )
    matches: list[bool] = [
        hmac.compare_digest(candidate.encode("utf-8"), stored)
        for candidate in candidates
    ]
    return any(matches)
