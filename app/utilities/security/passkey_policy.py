"""
The rules of passkey ceremonies: the signature counter of a copied
authenticator, the refusals and their reasons.
"""

from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.passkey_errors import (
    PasskeyRejectedError,
    PasskeysUnavailableError,
)
from app.schemas.typings.passkeys.constrained_integers import WebAuthnSignCount
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

PASSKEY_REJECTED_CODE: ErrorReasonCode = ErrorReasonCode("passkey_rejected")
PASSKEY_CLONE_SUSPECTED_CODE: ErrorReasonCode = ErrorReasonCode(
    "passkey_clone_suspected"
)
PASSKEYS_UNAVAILABLE_CODE: ErrorReasonCode = ErrorReasonCode("passkeys_unavailable")
PASSKEY_REJECTED_MESSAGE: str = "The passkey could not be confirmed. Try again."
CLONE_SUSPECTED_MESSAGE: str = (
    "This passkey was refused: a copy of it may be in use. Remove it, add it "
    "again, and use another way to sign in now."
)
PASSKEYS_UNAVAILABLE_MESSAGE: str = "Passkeys are not available here."


def is_sign_count_regressed(
    stored: WebAuthnSignCount, presented: WebAuthnSignCount
) -> bool:
    """
    WebAuthn §6.1.1: an authenticator that keeps a counter reports a
    larger one with every signature. A counter not above the stored one
    (while either is not zero) means two authenticators sign with the same
    key: a copy. Synced passkeys report 0 every time and pass.
    """

    return (int(stored) > 0 or int(presented) > 0) and int(presented) <= int(stored)


def passkey_rejected(message: str = PASSKEY_REJECTED_MESSAGE) -> PasskeyRejectedError:
    """HTTP 422 with the reason `passkey_rejected`."""

    return PasskeyRejectedError(
        message,
        reasons=[
            ErrorReason(code=PASSKEY_REJECTED_CODE, message=ErrorReasonMessage(message))
        ],
    )


def clone_suspected() -> PasskeyRejectedError:
    """HTTP 422 with the reason `passkey_clone_suspected`."""

    return PasskeyRejectedError(
        CLONE_SUSPECTED_MESSAGE,
        reasons=[
            ErrorReason(
                code=PASSKEY_CLONE_SUSPECTED_CODE,
                message=ErrorReasonMessage(CLONE_SUSPECTED_MESSAGE),
            )
        ],
    )


def passkeys_unavailable(
    message: str = PASSKEYS_UNAVAILABLE_MESSAGE,
) -> PasskeysUnavailableError:
    """HTTP 409 with the reason `passkeys_unavailable`."""

    return PasskeysUnavailableError(
        message,
        reasons=[
            ErrorReason(
                code=PASSKEYS_UNAVAILABLE_CODE, message=ErrorReasonMessage(message)
            )
        ],
    )
