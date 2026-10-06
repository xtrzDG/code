"""
A resource's calendars as the cabinet shows and changes them: the Google
calendar that blocks it, the iCal feeds it imports, its booking system,
its iCal export, how each source synced and the busy times ahead.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import (
    BookingSystemKind,
    BusyTimeSource,
    CalendarSyncProblem,
)
from app.schemas.typings.bookings.booleans import (
    IsCalendarConnected,
    IsCalendarIntegrationConfigured,
)
from app.schemas.typings.bookings.constrained_strings import CalendarSyncErrorSummary
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ExternalCalendarId, ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.booleans import IsIcalExportOn
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyBlockCount,
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
    CalendarFeedHost,
    IcalExportUrl,
)
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.calendar_sync.strings import BookingSystemResourceTitle


class BusySourceStatusView(ImmutableDTO):
    """How a source synced last; `problem` is why its last read failed."""

    last_attempt_at: Microseconds | None = None
    last_synced_at: Microseconds | None = None
    block_count: BusyBlockCount = BusyBlockCount(0)
    problem: CalendarSyncProblem | None = None
    problem_detail: CalendarSyncErrorSummary | None = None


class GoogleCalendarSourceView(ImmutableDTO):
    """
    The Google calendar that blocks the resource. `is_available`: this
    server can connect Google Calendar; `is_connected`: the business did.
    """

    is_available: IsCalendarIntegrationConfigured
    is_connected: IsCalendarConnected
    calendar_id: ExternalCalendarId | None = None
    status: BusySourceStatusView | None = None


class IcalImportView(ImmutableDTO):
    """An imported feed: its host only (the address is a secret)."""

    feed_id: IcalImportFeedId
    host: CalendarFeedHost
    added_at: Microseconds
    status: BusySourceStatusView


class IcalExportView(ImmutableDTO):
    """Whether the resource's export address exists, and when it was read."""

    is_on: IsIcalExportOn
    created_at: Microseconds | None = None
    last_read_at: Microseconds | None = None


class BookingSystemView(ImmutableDTO):
    """The booking system the resource follows (its key is never shown)."""

    kind: BookingSystemKind
    external_resource_id: BookingSystemResourceId
    external_resource_title: BookingSystemResourceTitle | None = None
    added_at: Microseconds
    status: BusySourceStatusView


class BusyTimeView(ImmutableDTO):
    """One busy time ahead and where it came from (a feed's host for iCal)."""

    source: BusyTimeSource
    feed_host: CalendarFeedHost | None = None
    starts_at: BusyStartsAtUnixSeconds
    ends_at: BusyEndsAtUnixSeconds


class ResourceCalendarView(ImmutableDTO):
    """
    The calendars of one resource: every source that blocks it, its export,
    the booking systems it may follow, when it syncs next, and the next
    busy times (at most 20) its sources reported.
    """

    business_id: BusinessId
    resource_id: ResourceId
    resource_name: ResourceName
    google: GoogleCalendarSourceView
    ical_imports: list[IcalImportView]
    ical_export: IcalExportView
    booking_system: BookingSystemView | None = None
    booking_system_kinds: list[BookingSystemKind]
    next_sync_at: Microseconds | None = None
    upcoming_busy_times: list[BusyTimeView]


class IcalExportCreated(ImmutableDTO):
    """The new export address, shown this once, and the resource's calendars."""

    url: IcalExportUrl
    calendar: ResourceCalendarView
