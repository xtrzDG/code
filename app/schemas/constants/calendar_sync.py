"""Where a resource's busy times come from, and why a source did not sync."""

from enum import StrEnum


class BusyTimeSource(StrEnum):
    """
    A calendar outside the platform whose busy times block a resource:
    the Google calendar linked to it (free/busy of the connected account),
    an imported iCal feed (Airbnb, Booking.com, Vrbo, any public calendar)
    or a booking system (Cal.com).
    """

    GOOGLE = "google"
    ICAL = "ical"
    BOOKING_SYSTEM = "booking_system"


class BookingSystemKind(StrEnum):
    """
    The booking systems the platform reads busy times from and writes its
    bookings to (one adapter each, in the connector registry).
    """

    CAL_COM = "cal_com"


class CalendarSyncProblem(StrEnum):
    """
    Why the last read of a source failed; the cabinet explains each one in
    the owner's language. The busy times read before stay in force.
    """

    # Google: the business has no connected calendar, or its consent lacks
    # the read permission (connected before availability was read) or ran out.
    NOT_CONNECTED = "not_connected"
    NEEDS_RECONNECT = "needs_reconnect"
    # The calendar, feed or event type is not there (any more).
    NOT_FOUND = "not_found"
    # The key or the address was refused (HTTP 401/403).
    ACCESS_DENIED = "access_denied"
    # The address is not a public http(s) address the platform may read.
    ADDRESS_REFUSED = "address_refused"
    # The source did not answer in time, or could not be reached.
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    # What came back is not a calendar (or is too large to be one).
    NOT_A_CALENDAR = "not_a_calendar"
    # Anything else the provider answered (an HTTP error, a broken answer).
    PROVIDER_ERROR = "provider_error"


class IntegrationKind(StrEnum):
    """The integrations Settings → Integrations lists."""

    GOOGLE_CALENDAR = "google_calendar"
    ICAL_IMPORT = "ical_import"
    ICAL_EXPORT = "ical_export"
    CAL_COM = "cal_com"


class IntegrationState(StrEnum):
    """How an integration stands for a business."""

    # Nothing is set up.
    OFF = "off"
    # Set up and syncing.
    ON = "on"
    # Set up, but its last sync failed (see the resource's status).
    ATTENTION = "attention"
    # This server cannot offer it (Google OAuth credentials are missing).
    UNAVAILABLE = "unavailable"
