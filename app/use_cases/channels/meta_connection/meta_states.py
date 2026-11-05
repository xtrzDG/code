"""
The one-time states of Facebook sign-ins: made, hashed, and taken back when
Meta's window returns, bound to the owner, business and purpose that started
them (as Google Calendar's consent state is).
"""

import hashlib
import secrets

from typed_time_provider import Microseconds

from app.contracts.meta_connection import MetaConnectionStateRepoContract
from app.schemas.constants.meta_connection import (
    MetaConnectionPurpose,
    MetaConnectionRefusal,
)
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionState,
    MetaConnectionStateHash,
)
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId

STATE_TOKEN_BYTES: int = 32
MICROSECONDS_PER_SECOND: int = 1_000_000
# Meta's window takes a minute or two; Embedded Signup with a new number
# (a code by SMS) a few more.
STATE_LIFETIME_SECONDS: int = 15 * 60


def generate_state() -> MetaConnectionState:
    """An unguessable state for one sign-in."""

    return MetaConnectionState(secrets.token_urlsafe(STATE_TOKEN_BYTES))


def hash_state(state: MetaConnectionState) -> MetaConnectionStateHash:
    return MetaConnectionStateHash(hashlib.sha256(str(state).encode()).hexdigest())


def state_end(now: Microseconds) -> Microseconds:
    return Microseconds(int(now) + STATE_LIFETIME_SECONDS * MICROSECONDS_PER_SECOND)


def meta_refusal(
    refusal: MetaConnectionRefusal,
    message: str,
    error_type: type[ApplicationError] = ValidationFailedError,
) -> ApplicationError:
    """An error whose reason code tells the cabinet what to say."""

    return error_type(
        message,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(refusal.value),
                message=ErrorReasonMessage(message),
            )
        ],
    )


def link_expired() -> ApplicationError:
    return meta_refusal(
        MetaConnectionRefusal.LINK_EXPIRED,
        "This Facebook sign-in has ended or was not started here. Start it again.",
    )


def take_state(
    state_repo: MetaConnectionStateRepoContract,
    business_id: BusinessId,
    user_id: UserId,
    state: MetaConnectionState,
    purpose: MetaConnectionPurpose,
    now: Microseconds,
) -> MetaConnectionStateDocument:
    """
    Mark the sign-in used before Meta's code is exchanged, in one step, so
    the same sign-in is never finished twice (a second attempt, even at
    the same moment, finds it used). Someone else's, another purpose's, an
    ended or a used sign-in raises LINK_EXPIRED and is left as it is.
    """

    def consume(
        stored: MetaConnectionStateDocument,
    ) -> MetaConnectionStateDocument | None:
        if not is_open_for(stored, user_id, purpose, now) or stored.is_consumed:
            return None

        return stored.model_copy(update={"is_consumed": True, "updated_at": now})

    taken: MetaConnectionStateDocument | None = state_repo.modify(
        business_id, hash_state(state), consume
    )
    if taken is None:
        raise link_expired()

    return taken


def is_open_for(
    stored: MetaConnectionStateDocument,
    user_id: UserId,
    purpose: MetaConnectionPurpose,
    now: Microseconds,
) -> bool:
    """The sign-in is this person's, for this purpose, and has not ended."""

    return (
        stored.user_id == user_id
        and stored.purpose is purpose
        and int(stored.expires_at) > int(now)
    )
