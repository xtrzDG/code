"""
Session rotation tickets: the one-time proof that the client asking for a
fresh token is the one that just raised its session to two factors.

A ticket carries 256 random bits and lives ROTATION_TICKET_TTL_SECONDS;
the session stores only its SHA-256 hash, and the hash is compared in
constant time. The old token keeps answering ROTATION_GRACE_SECONDS after
a rotation (the requests already on their way), as one factor without a
proof.
"""

import hmac
import secrets
from hashlib import sha256

from typed_time_provider import Microseconds

from app.schemas.domain.users import UserSessionDocument
from app.schemas.typings.users.constrained_strings import SessionRotationTicket
from app.schemas.typings.users.strings import SessionRotationTicketHash

MICROSECONDS_PER_SECOND: int = 1_000_000
ROTATION_TICKET_RANDOM_BYTES: int = 32
# The cabinet rotates right after the proof; two minutes cover a slow network.
ROTATION_TICKET_TTL_SECONDS: int = 120
# How long the old token still answers the requests already on their way
# with it, as a one-factor session that can confirm nothing; without this
# such a request would be refused and the cabinet would drop the new cookie.
ROTATION_GRACE_SECONDS: int = 30


def generate_rotation_ticket() -> SessionRotationTicket:
    """A new URL-safe ticket with 256 random bits (43 characters)."""

    return SessionRotationTicket(secrets.token_urlsafe(ROTATION_TICKET_RANDOM_BYTES))


def hash_rotation_ticket(ticket: SessionRotationTicket) -> SessionRotationTicketHash:
    """The SHA-256 hex digest of a ticket, the only stored form."""

    return SessionRotationTicketHash(sha256(str(ticket).encode("utf-8")).hexdigest())


def ticket_expiry(now: Microseconds) -> Microseconds:
    ttl: int = ROTATION_TICKET_TTL_SECONDS * MICROSECONDS_PER_SECOND
    return Microseconds(int(now) + ttl)


def grace_end(now: Microseconds) -> Microseconds:
    """When the old token of a session rotated now stops answering."""

    return Microseconds(int(now) + ROTATION_GRACE_SECONDS * MICROSECONDS_PER_SECOND)


def holds_ticket(
    session: UserSessionDocument,
    ticket_hash: SessionRotationTicketHash,
    now: Microseconds,
) -> bool:
    """
    The session has not rotated yet and waits for exactly this ticket,
    which has not expired.
    """

    if (
        session.rotated_at is not None
        or session.rotation_ticket_hash is None
        or session.rotation_ticket_expires_at is None
        or session.rotation_proven_at is None
    ):
        return False

    return int(now) < int(session.rotation_ticket_expires_at) and hmac.compare_digest(
        str(session.rotation_ticket_hash), str(ticket_hash)
    )
