"""
Authenticator codes (RFC 6238 TOTP: HMAC-SHA1, six digits, 30-second
steps), the parameters every common authenticator app uses by default.
"""

import hmac

import pyotp

from app.schemas.typings.mfa.constrained_integers import TotpTimeStep
from app.schemas.typings.mfa.constrained_strings import TotpCode, TotpSecret
from app.schemas.typings.mfa.strings import (
    TotpAccountLabel,
    TotpIssuerName,
    TotpProvisioningUri,
)

TOTP_STEP_SECONDS: int = 30
MICROSECONDS_PER_SECOND: int = 1_000_000
# A code of the previous or the next step is accepted too: phones' clocks
# drift and people type slowly.
ACCEPTED_STEP_DRIFT: int = 1


def generate_totp_secret() -> TotpSecret:
    """160 random bits from the OS CSPRNG, in base32 (32 characters)."""

    return TotpSecret(pyotp.random_base32(length=32))


def totp_provisioning_uri(
    secret: TotpSecret,
    account_label: TotpAccountLabel,
    issuer: TotpIssuerName,
) -> TotpProvisioningUri:
    """The `otpauth://totp/…` address an authenticator app reads from a QR code."""

    uri: str = pyotp.TOTP(str(secret)).provisioning_uri(
        name=str(account_label), issuer_name=str(issuer)
    )
    return TotpProvisioningUri(uri)


def current_totp_step(now_microseconds: int) -> TotpTimeStep:
    return TotpTimeStep(
        now_microseconds // MICROSECONDS_PER_SECOND // TOTP_STEP_SECONDS
    )


def totp_code_at(secret: TotpSecret, step: TotpTimeStep) -> TotpCode:
    """The code of a step (for tests and the code check)."""

    return TotpCode(pyotp.TOTP(str(secret)).generate_otp(int(step)))


def find_totp_step(
    secret: TotpSecret,
    code: TotpCode,
    now_microseconds: int,
    last_used_step: TotpTimeStep | None,
) -> TotpTimeStep | None:
    """
    The step the code belongs to (the current one, or one step before or
    after), compared in constant time; None when it matches none or only
    a step already used (`last_used_step` or earlier), so a code works once.
    """

    current: int = int(current_totp_step(now_microseconds))
    matched: TotpTimeStep | None = None
    for offset in range(-ACCEPTED_STEP_DRIFT, ACCEPTED_STEP_DRIFT + 1):
        step: TotpTimeStep = TotpTimeStep(current + offset)
        if last_used_step is not None and step <= last_used_step:
            continue

        candidate: TotpCode = totp_code_at(secret, step)
        if hmac.compare_digest(str(candidate).encode(), str(code).encode()):
            matched = step

    return matched
