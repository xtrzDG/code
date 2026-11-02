"""
OAuth state values that bind a calendar callback to a business, and the
PKCE pair (RFC 7636, S256) that binds the code to the flow that asked.
"""

import base64
import hashlib
import secrets

from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationState,
    CalendarAuthorizationStateHash,
    CalendarCodeChallenge,
    CalendarCodeVerifier,
)

STATE_TOKEN_BYTES: int = 32
# 64 random bytes are 86 base64url characters (RFC 7636: 43 to 128).
CODE_VERIFIER_BYTES: int = 64


def generate_authorization_state() -> CalendarAuthorizationState:
    """Unguessable random state for one consent attempt."""

    return CalendarAuthorizationState(secrets.token_urlsafe(STATE_TOKEN_BYTES))


def hash_authorization_state(
    state: CalendarAuthorizationState,
) -> CalendarAuthorizationStateHash:
    return CalendarAuthorizationStateHash(
        hashlib.sha256(str(state).encode("utf-8")).hexdigest()
    )


def generate_code_verifier() -> CalendarCodeVerifier:
    """A random verifier of unreserved characters (base64url, no padding)."""

    return CalendarCodeVerifier(secrets.token_urlsafe(CODE_VERIFIER_BYTES))


def code_challenge_of(verifier: CalendarCodeVerifier) -> CalendarCodeChallenge:
    """S256: BASE64URL(SHA-256(ASCII(verifier))) without padding."""

    digest: bytes = hashlib.sha256(str(verifier).encode("ascii")).digest()
    return CalendarCodeChallenge(
        base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    )
