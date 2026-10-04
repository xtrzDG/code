"""
Device sessions: checking a bearer token on each request, and a person's
own list of signed-in devices with ending one or all the others.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.users import SessionDeviceKind
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.booleans import IsCurrentSession
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.schemas.typings.users.strings import (
    AccessToken,
    SessionBrowserName,
    SessionOperatingSystem,
)


class SessionCheck(ImmutableDTO):
    """
    One signed-in request: its bearer token, where it comes from, the
    browser it names, and whether it reads or changes (`access_mode`, from
    the HTTP method; the support access check refuses changes to
    read-only support).
    """

    access_token: AccessToken
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None
    access_mode: BusinessAccessMode = BusinessAccessMode.WRITE


class SessionActivity(ImmutableDTO):
    """
    A use of a session worth recording (at most every five minutes): when
    and from where, the browser it named, and its new expiries.
    """

    seen_at: Microseconds
    seen_ip: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None
    idle_expires_at: Microseconds
    expires_at: Microseconds


class SessionDevice(ImmutableDTO):
    """The browser, system and kind of device a User-Agent names."""

    kind: SessionDeviceKind = SessionDeviceKind.UNKNOWN
    browser: SessionBrowserName | None = None
    operating_system: SessionOperatingSystem | None = None


class UserSessionView(ImmutableDTO):
    """
    One signed-in device of the person (Account → Security): what it is,
    where and when it signed in, when it was last used and from where,
    how it was signed in, and when it ends by itself (unused until
    `idle_expires_at`, or at `expires_at` whatever happens). The request's
    own session is `is_current`.
    """

    id: UserSessionId
    device: SessionDevice
    auth_level: AuthLevel
    created_at: Microseconds
    created_ip: ClientIpAddress | None = None
    last_seen_at: Microseconds
    last_seen_ip: ClientIpAddress | None = None
    expires_at: Microseconds
    idle_expires_at: Microseconds | None = None
    is_current: IsCurrentSession = False


class UserSessionList(ImmutableDTO):
    """
    The person's live sessions, the current one first, then the most
    recently used (a short list: expired sessions are gone).
    """

    items: list[UserSessionView] = Field(default_factory=list[UserSessionView])


class SessionsQuery(ImmutableDTO):
    """The live sessions of the signed-in person."""

    user_id: UserId


class RevokeSessionCommand(ImmutableDTO):
    """End one session of the signed-in person (a lost phone)."""

    user_id: UserId
    session_id: UserSessionId
    client_ip_address: ClientIpAddress | None = None


class RevokeOtherSessionsCommand(ImmutableDTO):
    """End every session of the person except the request's own."""

    user_id: UserId
    client_ip_address: ClientIpAddress | None = None


class RevokedSessionsView(ImmutableDTO):
    """How many sessions were ended."""

    revoked_count: DocumentCount
