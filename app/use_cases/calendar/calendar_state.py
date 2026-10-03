"""OAuth state values that bind a calendar callback to a business."""

import hashlib
import secrets

from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationState,
    CalendarAuthorizationStateHash,
)

STATE_TOKEN_BYTES: int = 32


def generate_authorization_state() -> CalendarAuthorizationState:
    """Unguessable random state for one consent attempt."""

    return CalendarAuthorizationState(secrets.token_urlsafe(STATE_TOKEN_BYTES))


def hash_authorization_state(
    state: CalendarAuthorizationState,
) -> CalendarAuthorizationStateHash:
    return CalendarAuthorizationStateHash(
        hashlib.sha256(str(state).encode("utf-8")).hexdigest()
    )
