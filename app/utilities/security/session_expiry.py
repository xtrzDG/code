"""
When a session ends and when a use of it is worth recording: the idle
expiry slides with use (a week for owners and staff, twelve hours for
platform admins), the absolute end never moves later (30 days, a day for
platform admins), and the last use is written at most every five minutes.
"""

from typed_time_provider import Microseconds

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import SessionActivity
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.constrained_strings import SessionUserAgent

MICROSECONDS_PER_SECOND: int = 1_000_000
LAST_SEEN_WRITE_INTERVAL_MICROSECONDS: int = 5 * 60 * MICROSECONDS_PER_SECOND


def is_session_over(session: UserSessionDocument, now: Microseconds) -> bool:
    """Past its absolute end, or unused until its idle expiry."""

    return int(now) >= int(session.expires_at) or (
        session.idle_expires_at is not None and int(now) >= int(session.idle_expires_at)
    )


def idle_timeout_microseconds(settings: AppSettings, is_admin: bool) -> int:
    seconds: int = int(
        settings.sessions.admin_idle_timeout_seconds
        if is_admin
        else settings.sessions.idle_timeout_seconds
    )
    return seconds * MICROSECONDS_PER_SECOND


def lifetime_microseconds(settings: AppSettings, is_admin: bool) -> int:
    seconds: int = int(
        settings.sessions.admin_lifetime_seconds
        if is_admin
        else settings.session_lifetime_seconds
    )
    return seconds * MICROSECONDS_PER_SECOND


def opening_expiries(
    settings: AppSettings, is_admin: bool, now: Microseconds
) -> tuple[Microseconds, Microseconds]:
    """(absolute end, idle expiry) of a session opened now."""

    expires_at: int = int(now) + lifetime_microseconds(settings, is_admin)
    idle: int = min(
        int(now) + idle_timeout_microseconds(settings, is_admin), expires_at
    )
    return Microseconds(expires_at), Microseconds(idle)


def is_use_recent(session: UserSessionDocument, now: Microseconds) -> bool:
    """The last recorded use is under five minutes old: nothing to write."""

    return session.last_seen_at is not None and (
        int(now) - int(session.last_seen_at) < LAST_SEEN_WRITE_INTERVAL_MICROSECONDS
    )


def next_activity(
    session: UserSessionDocument,
    settings: AppSettings,
    is_admin: bool,
    now: Microseconds,
    client_ip_address: ClientIpAddress | None,
    user_agent: SessionUserAgent | None,
) -> SessionActivity:
    """
    The use to record now: the idle expiry slides forward, never past the
    absolute end. A person who became a platform admin after signing in
    gets the admin limits at this use (their session may end with it).
    """

    expires_at: int = int(session.expires_at)
    if is_admin:
        expires_at = min(
            expires_at,
            int(session.created_at) + lifetime_microseconds(settings, is_admin=True),
        )
    idle_expires_at: int = min(
        int(now) + idle_timeout_microseconds(settings, is_admin), expires_at
    )
    return SessionActivity(
        seen_at=now,
        seen_ip=client_ip_address,
        user_agent=user_agent,
        idle_expires_at=Microseconds(idle_expires_at),
        expires_at=Microseconds(expires_at),
    )
