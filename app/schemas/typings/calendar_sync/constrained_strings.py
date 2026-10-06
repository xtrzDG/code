"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class BookingSystemResourceId(BaseConstrainedTypedString):
    """
    What a resource is in an outside booking system: for Cal.com the id of
    the event type whose bookings make the resource busy and that new
    bookings go to.

    Example:
        external_id = BookingSystemResourceId("1203845")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9][A-Za-z0-9._:\-]*$"


class CalendarFeedHost(BaseConstrainedTypedString):
    """
    The host of a calendar feed a business imports (`www.airbnb.com`),
    shown in the cabinet instead of the secret address itself.

    Example:
        host = CalendarFeedHost("www.airbnb.com")
    """

    min_length = 1
    max_length = 253
    pattern = r"^[A-Za-z0-9._\-\[\]:]+$"


class CalendarFeedUrl(BaseConstrainedTypedString):
    """
    The address of an iCalendar feed a business imports (Airbnb,
    Booking.com, Vrbo, a public calendar): https, http or webcal. It is
    secret (whoever has it sees the calendar), so it is stored encrypted
    and never shown again in full.

    Example:
        url = CalendarFeedUrl("https://www.airbnb.com/calendar/ical/123.ics?s=x")
    """

    min_length = 12
    max_length = 2048
    pattern = r"^(?i:https?|webcal)://[^\s/?#]+([/?#][^\s]*)?$"


class IcalExportTokenHash(BaseConstrainedTypedString):
    """SHA-256 (hex) of the secret token in a resource's iCal export address."""

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class IcalExportUrl(BaseConstrainedTypedString):
    """
    The address of a resource's busy times as an iCalendar feed, to paste
    into Airbnb, Booking.com or any calendar. Shown once, when it is made.

    Example:
        url = IcalExportUrl("https://api.example/v1/public/ical/abc.ics")
    """

    min_length = 12
    max_length = 2048
    pattern = r"^https?://[^\s/?#]+/[^\s]*\.ics$"


# Keep abc order for all non example types, if possible.
