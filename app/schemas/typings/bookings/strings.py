"""Keep abc order."""

from base_typed_string import BaseTypedString


class BookingCalendarText(BaseTypedString):
    """An iCalendar file (RFC 5545) of one booking, as a guest saves it."""


class BookingNote(BaseTypedString):
    """Free-form wish attached to a booking ("high chair", "late arrival")."""


class CalendarAccessToken(BaseTypedString):
    """Short-lived OAuth access token of a connected calendar. Never logged."""


class CalendarAuthorizationCode(BaseTypedString):
    """One-time OAuth authorization code returned to the calendar callback."""


class CalendarAuthorizationState(BaseTypedString):
    """
    Random OAuth `state` value that binds a calendar callback to the business
    and the owner who started the connection. Only its hash is stored.
    """


class CalendarAuthorizationStateHash(BaseTypedString):
    """SHA-256 hex digest of a calendar OAuth state, the only stored form."""


class CalendarDisplayName(BaseTypedString):
    """
    Title of a connected calendar as the provider shows it (for a primary
    Google calendar usually the account's e-mail address).
    """


class CalendarEventDescription(BaseTypedString):
    """Body text of a calendar event created for a booking."""


class CalendarEventId(BaseTypedString):
    """Identifier of an event at the calendar provider."""


class CalendarEventTitle(BaseTypedString):
    """Title of a calendar event created for a booking."""


class CalendarProviderErrorCode(BaseTypedString):
    """
    Error code the calendar provider puts on the OAuth callback instead of
    a code, e.g. "access_denied" when the owner declines.
    """


class CalendarRefreshToken(BaseTypedString):
    """Long-lived OAuth refresh token of a connected calendar. Never logged."""


class ExternalCalendarId(BaseTypedString):
    """
    Calendar identifier at the provider, e.g. "primary" or a shared calendar
    address such as "abc123@group.calendar.google.com".
    """


class LeadBudgetText(BaseTypedString):
    """Budget exactly as the customer stated it, in any currency or words."""


class LeadDetails(BaseTypedString):
    """What the customer wants from a manager (banquet, group stay, order)."""


class ResourceName(BaseTypedString):
    """Name of a bookable resource, e.g. "Table 4", "VR arena 2", "Nino"."""


class ResourceReference(BaseTypedString):
    """
    How the language model names a bookable resource (a master, a doctor, a
    room): its id from the facts or a tool result, or its name as the
    customer wrote it, in any script ("Nino", "ნინო", "Нино").
    """


class ScheduleExceptionNote(BaseTypedString):
    """Why a day is closed or has special hours ("Orthodox Christmas")."""


# Keep abc order for all non example types, if possible.
