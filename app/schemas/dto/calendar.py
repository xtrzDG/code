"""Google Calendar connection: the consent outcome and the cabinet's status view."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.calendar import CalendarConnectionFailure
from app.schemas.dto.operations import CalendarConnectionView
from app.schemas.typings.bookings.booleans import (
    IsCalendarConnected,
    IsCalendarIntegrationConfigured,
)
from app.schemas.typings.bookings.constrained_strings import CalendarSyncErrorSummary
from app.schemas.typings.bookings.strings import (
    CalendarDisplayName,
    ExternalCalendarId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId


class CalendarConnectionOutcome(ImmutableDTO):
    """
    How the OAuth callback ended: the new connection, or why it failed.

    `business_id` is known whenever the callback carried a state we issued
    (even an expired or used one), so the owner can be sent back to that
    business's Channels page; it is None for an unknown state.
    """

    business_id: BusinessId | None = None
    connection: CalendarConnectionView | None = None
    failure: CalendarConnectionFailure | None = None


class CalendarConnectionStatusQuery(ImmutableDTO):
    """A business's Google Calendar connection, for its owners and staff."""

    business_id: BusinessId


class CalendarConnectionStatusView(ImmutableDTO):
    """
    Whether Google Calendar is connected and how syncing goes. Tokens are
    never returned.

    `is_configured` tells whether this server can connect Google Calendar
    at all (Google OAuth credentials and APP_BASE_URL are set). The sync
    error is a short provider reason; it clears after the next booking that
    syncs.
    """

    business_id: BusinessId
    is_configured: IsCalendarIntegrationConfigured
    is_connected: IsCalendarConnected
    calendar_id: ExternalCalendarId | None = None
    calendar_name: CalendarDisplayName | None = None
    connected_at: Microseconds | None = None
    last_synced_at: Microseconds | None = None
    last_sync_error: CalendarSyncErrorSummary | None = None
    last_sync_error_at: Microseconds | None = None
