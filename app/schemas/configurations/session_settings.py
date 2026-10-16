from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.users.constrained_integers import (
    SessionIdleTimeoutSeconds,
    SessionLifetimeSeconds,
)

DEFAULT_SESSION_IDLE_TIMEOUT_SECONDS: int = 7 * 24 * 60 * 60
DEFAULT_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS: int = 12 * 60 * 60
DEFAULT_ADMIN_SESSION_LIFETIME_SECONDS: int = 24 * 60 * 60


class SessionSettings(ImmutableDTO):
    """
    How long a session lives without use: a week for owners and staff
    (SESSION_IDLE_TIMEOUT_SECONDS), twelve hours for platform admins
    (ADMIN_SESSION_IDLE_TIMEOUT_SECONDS); and at most, whatever its use,
    a day for platform admins (ADMIN_SESSION_LIFETIME_SECONDS; everyone
    else: SESSION_LIFETIME_SECONDS, 30 days).
    """

    idle_timeout_seconds: SessionIdleTimeoutSeconds = SessionIdleTimeoutSeconds(
        DEFAULT_SESSION_IDLE_TIMEOUT_SECONDS
    )
    admin_idle_timeout_seconds: SessionIdleTimeoutSeconds = SessionIdleTimeoutSeconds(
        DEFAULT_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS
    )
    admin_lifetime_seconds: SessionLifetimeSeconds = SessionLifetimeSeconds(
        DEFAULT_ADMIN_SESSION_LIFETIME_SECONDS
    )
