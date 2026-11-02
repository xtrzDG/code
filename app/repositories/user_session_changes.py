"""
The changes UserSessionRepository makes to one stored session, each run
inside the collection's `modify` (one atomic read-and-write: a row lock on
Postgres, the collection lock in memory), so two requests on the same
session never undo each other's write. A change returns None to write
nothing.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import SessionActivity
from app.schemas.typings.users.strings import SessionRotationTicketHash
from app.utilities.security.session_rotation_tickets import holds_ticket

SessionChange = Callable[[UserSessionDocument], UserSessionDocument | None]


def recorded_authentication(
    auth_level: AuthLevel, authenticated_at: Microseconds
) -> SessionChange:
    """
    The level and proof written on the session itself; a waiting rotation
    ticket goes (the proof it held is stale now). A rotated session takes
    nothing: its old token never gains a level or a proof again. Nor does
    a session stored as one factor take two in place (lowered since the
    request read it): that raise waits as a rotation ticket.
    """

    def record(session: UserSessionDocument) -> UserSessionDocument | None:
        if session.rotated_at is not None:
            return None

        if (
            auth_level is AuthLevel.TWO_FACTOR
            and session.auth_level is not AuthLevel.TWO_FACTOR
        ):
            return None

        session.auth_level = auth_level
        session.authenticated_at = authenticated_at
        session.updated_at = authenticated_at
        _drop_ticket(session)
        return session

    return record


def recorded_activity(activity: SessionActivity) -> SessionChange:
    """
    A use of the session. Its absolute end only ever moves earlier (the
    stored one wins over a later one computed from an older read, such as
    a rotation's wind-down that came in between), and the idle expiry
    never passes it.
    """

    def record(session: UserSessionDocument) -> UserSessionDocument:
        expires_at: int = min(int(session.expires_at), int(activity.expires_at))
        session.last_seen_at = activity.seen_at
        session.last_seen_ip = activity.seen_ip
        if activity.user_agent is not None:
            session.user_agent = activity.user_agent
        session.expires_at = Microseconds(expires_at)
        session.idle_expires_at = Microseconds(
            min(int(activity.idle_expires_at), expires_at)
        )
        session.updated_at = activity.seen_at
        return session

    return record


def held_ticket(
    ticket_hash: SessionRotationTicketHash,
    proven_at: Microseconds,
    expires_at: Microseconds,
) -> SessionChange:
    """A rotation ticket waiting on a session not rotated yet (the newest wins)."""

    def hold(session: UserSessionDocument) -> UserSessionDocument | None:
        if session.rotated_at is not None:
            return None

        session.rotation_ticket_hash = ticket_hash
        session.rotation_ticket_expires_at = expires_at
        session.rotation_proven_at = proven_at
        session.updated_at = proven_at
        return session

    return hold


def wound_down(
    ticket_hash: SessionRotationTicketHash,
    now: Microseconds,
    old_token_ends_at: Microseconds,
    taken: list[UserSessionDocument],
) -> SessionChange:
    """
    Take the session's ticket (when it matches and has not expired) and
    wind the session down in the same step: one factor, no proof, no
    ticket, over at `old_token_ends_at` at the latest. The session as it
    was before goes into `taken`.
    """

    def wind_down(session: UserSessionDocument) -> UserSessionDocument | None:
        if not holds_ticket(session, ticket_hash, now):
            return None

        taken.append(session.model_copy(deep=True))
        ends_at: int = min(int(session.expires_at), int(old_token_ends_at))
        session.auth_level = AuthLevel.ONE_FACTOR
        session.authenticated_at = None
        session.expires_at = Microseconds(ends_at)
        session.idle_expires_at = Microseconds(
            ends_at
            if session.idle_expires_at is None
            else min(int(session.idle_expires_at), ends_at)
        )
        session.rotated_at = now
        session.updated_at = now
        _drop_ticket(session)
        return session

    return wind_down


def set_level(
    auth_level: AuthLevel, now: Microseconds, changed: list[UserSessionDocument]
) -> SessionChange:
    """
    The session counts as `auth_level`; when it last proved its person
    stays. A waiting rotation ticket goes too (the proof it held may no
    longer stand). Sessions whose level changed go into `changed`.
    """

    def change(session: UserSessionDocument) -> UserSessionDocument | None:
        # A legacy session without a level already counts as one factor.
        current: AuthLevel = session.auth_level or AuthLevel.ONE_FACTOR
        if current is auth_level and session.rotation_ticket_hash is None:
            return None

        if current is not auth_level:
            changed.append(session)
        session.auth_level = auth_level
        session.updated_at = now
        _drop_ticket(session)
        return session

    return change


def _drop_ticket(session: UserSessionDocument) -> None:
    session.rotation_ticket_hash = None
    session.rotation_ticket_expires_at = None
    session.rotation_proven_at = None
