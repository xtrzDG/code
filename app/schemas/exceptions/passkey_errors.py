"""Refusals of passkey ceremonies."""

from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.mfa_errors import WrongCodeError


class PasskeyRejectedError(WrongCodeError):
    """
    A passkey's answer that does not check out: a wrong or reused
    challenge, another site's origin, a bad signature, an unknown passkey,
    or a counter that went backwards (a copied authenticator; reason
    `passkey_clone_suspected`). HTTP 422 with the reason
    `passkey_rejected`, never 401: a failed confirmation does not end the
    session. A sign-in step counts it as a wrong attempt.
    """


class PasskeysUnavailableError(ConflictError):
    """
    This server is not set up for passkeys (no WEBAUTHN_RP_ID and no
    cabinet address), or the person has none to use: HTTP 409 with the
    reason `passkeys_unavailable`.
    """
