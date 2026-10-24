"""
Google Calendar: connecting and disconnecting a calendar, the token grant
and the drafts of the events bookings put on it.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.bookings.booleans import WasCalendarConnected
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    CalendarTokenLifetimeSeconds,
)
from app.schemas.typings.bookings.constrained_strings import CalendarAuthorizationUrl
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarEventDescription,
    CalendarEventTitle,
    CalendarProviderErrorCode,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.users.prefixed_id import UserId


class StartCalendarConnectionCommand(ImmutableDTO):
    """Owner starts connecting Google Calendar to a business."""

    business_id: BusinessId
    user_id: UserId


class CalendarConnectUrlView(ImmutableDTO):
    """Consent page to open; the link stops working at `expires_at`."""

    authorization_url: CalendarAuthorizationUrl
    expires_at: Microseconds


class CompleteCalendarConnectionCommand(ImmutableDTO):
    """
    OAuth callback values: the state we issued and Google's code, or the
    error Google reports instead of a code (the owner declined), brought
    back by the signed-in user who must be the one that started the flow.
    """

    user_id: UserId
    state: CalendarAuthorizationState | None = None
    code: CalendarAuthorizationCode | None = None
    provider_error: CalendarProviderErrorCode | None = None


class CalendarConnectionView(ImmutableDTO):
    """A connected calendar of a business."""

    business_id: BusinessId
    calendar_id: ExternalCalendarId
    connected_at: Microseconds


class DisconnectCalendarCommand(ImmutableDTO):
    """Owner disconnects Google Calendar; the token is revoked at Google."""

    business_id: BusinessId


class CalendarDisconnectResult(ImmutableDTO):
    """Whether a calendar was connected before the call."""

    business_id: BusinessId
    was_connected: WasCalendarConnected


class CalendarTokenGrant(ImmutableDTO):
    """
    Tokens returned by the provider. A refresh token comes only with the
    first consent (offline access); refreshes return a new access token only.
    """

    access_token: CalendarAccessToken
    refresh_token: CalendarRefreshToken | None = None
    expires_in: CalendarTokenLifetimeSeconds


class CalendarEventText(ImmutableDTO):
    """Owner-language title and description of a booking's calendar event."""

    title: CalendarEventTitle
    description: CalendarEventDescription


class CalendarEventDraft(ImmutableDTO):
    """Event to create or update at the provider; times are UTC seconds."""

    title: CalendarEventTitle
    description: CalendarEventDescription
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    timezone: TimezoneName
