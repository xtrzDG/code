"""One-time login codes: generation and keyed hashing.

Only the hash of a code is stored. It is an HMAC-SHA256 keyed with the
challenge id, so the same code in two challenges gives different hashes, and
codes are compared in constant time.
"""

import hmac
import secrets
from hashlib import sha256

from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import OtpCodeHash

OTP_CODE_DIGITS: int = 6


def generate_otp_code() -> OtpCode:
    """Return a uniformly random six-digit code from the OS CSPRNG."""

    random_number: int = secrets.randbelow(10**OTP_CODE_DIGITS)
    return OtpCode(f"{random_number:0{OTP_CODE_DIGITS}d}")


def hash_otp_code(challenge_id: OtpChallengeId, code: OtpCode) -> OtpCodeHash:
    """Return the hex HMAC-SHA256 of a code keyed with its challenge id."""

    digest: str = hmac.new(
        key=str(challenge_id).encode("utf-8"),
        msg=str(code).encode("utf-8"),
        digestmod=sha256,
    ).hexdigest()
    return OtpCodeHash(digest)


def is_otp_code_matching(
    challenge_id: OtpChallengeId,
    code: OtpCode,
    code_hash: OtpCodeHash,
) -> bool:
    """Compare a typed code with the stored hash in constant time."""

    candidate_hash: OtpCodeHash = hash_otp_code(challenge_id, code)
    return hmac.compare_digest(
        str(candidate_hash).encode("utf-8"),
        str(code_hash).encode("utf-8"),
    )
