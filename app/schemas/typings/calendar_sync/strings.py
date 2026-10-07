"""Keep abc order."""

from base_typed_string import BaseTypedString


class BookingSystemApiKey(BaseTypedString):
    """
    The API key a business gives the platform for its booking system
    (Cal.com: "cal_live_..."). Stored only encrypted; never shown or logged.
    """


class BookingSystemBookingId(BaseTypedString):
    """A booking's identifier in an outside booking system (Cal.com `uid`)."""


class BookingSystemResourceTitle(BaseTypedString):
    """
    What the booking system calls the resource the platform follows there
    (a Cal.com event type's title), shown next to its id.
    """


class GoogleCalendarAccessRole(BaseTypedString):
    """
    What the connected Google account may do with a calendar of its list
    ("owner", "writer", "reader", "freeBusyReader").
    """


class IcalExportToken(BaseTypedString):
    """
    The secret in a resource's iCal export address. Shown once, when the
    address is made; only its hash is stored.
    """


class IcalFeedText(BaseTypedString):
    """
    A resource's busy times as iCalendar text (RFC 5545): one VCALENDAR,
    CRLF lines, folded at 75 octets.
    """


# Keep abc order for all non example types, if possible.
