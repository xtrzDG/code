"""
What the outside sources of busy times are asked for and answer: Google
free/busy and the account's calendar list, a booking system's bookings,
and the new bookings the platform writes there.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import (
    CalendarDisplayName,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.booleans import IsGoogleCalendarListReadable
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
)
from app.schemas.typings.calendar_sync.strings import (
    BookingSystemApiKey,
    BookingSystemBookingId,
    BookingSystemResourceTitle,
    GoogleCalendarAccessRole,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.constrained_strings import EmailAddress


class BusyWindow(ImmutableDTO):
    """The time a read covers (UTC seconds), from its start to its end."""

    starts_at: BusyStartsAtUnixSeconds
    ends_at: BusyEndsAtUnixSeconds


class BusyPeriod(ImmutableDTO):
    """One busy time a source reported (UTC seconds; the end after the start)."""

    starts_at: BusyStartsAtUnixSeconds
    ends_at: BusyEndsAtUnixSeconds


class GoogleCalendarEntry(ImmutableDTO):
    """A calendar on the connected Google account's list."""

    calendar_id: ExternalCalendarId
    name: CalendarDisplayName
    access_role: GoogleCalendarAccessRole
    is_primary: bool = False


class GoogleCalendarList(ImmutableDTO):
    """
    The calendars a resource can be linked to. `is_readable` is False, with
    the reason, when they cannot be listed: Google Calendar is not
    connected, or its consent predates reading calendars (reconnect).
    """

    is_readable: IsGoogleCalendarListReadable
    problem: CalendarSyncProblem | None = None
    items: list[GoogleCalendarEntry]


class BookingSystemCredentials(ImmutableDTO):
    """The business's key and what the resource is in its booking system."""

    api_key: BookingSystemApiKey
    external_resource_id: BookingSystemResourceId


class BookingSystemResource(ImmutableDTO):
    """What the booking system calls the resource (to show next to its id)."""

    external_resource_id: BookingSystemResourceId
    title: BookingSystemResourceTitle | None = None


class BookingSystemBookingDraft(ImmutableDTO):
    """
    A booking the platform writes to the booking system so the time is
    taken there too. Only the guest's name and, when known, e-mail go
    along; the time is UTC seconds. `platform_booking_id` marks it there
    as the platform's (its own bookings never block the resource twice,
    and a write repeated after a crash finds the one written before).
    """

    starts_at: BusyStartsAtUnixSeconds
    ends_at: BusyEndsAtUnixSeconds
    guest_name: ContactName
    guest_email: EmailAddress | None = None
    time_zone: TimezoneName
    language: LanguageTag
    platform_booking_id: BookingId | None = None


class BookingSystemRead(ImmutableDTO):
    """One read of a booking system: whose, what, how long it may take."""

    credentials: BookingSystemCredentials
    window: BusyWindow
    timeout: BusyTimeFetchSeconds


class BookingSystemBookingCreated(ImmutableDTO):
    """The booking system's identifier of the booking the platform wrote."""

    booking_id: BookingSystemBookingId
