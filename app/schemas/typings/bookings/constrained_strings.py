"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AssistantBookingNote(BaseConstrainedTypedString):
    """
    The customer's wish as the assistant passes it to create_booking or
    join_waitlist ("high chair", "late arrival"): 1 to 500 characters, no
    control characters except line breaks and tabs.

    Example:
        note = AssistantBookingNote("High chair for a toddler")
    """

    min_length = 1
    max_length = 500
    pattern = r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f]*\Z"


class AssistantLeadBudget(BaseConstrainedTypedString):
    """
    A request's budget as the assistant passes it to create_lead, in the
    customer's words ("around 1500 EUR"): 1 to 100 characters on one line.

    Example:
        budget = AssistantLeadBudget("around 1500 EUR")
    """

    min_length = 1
    max_length = 100
    pattern = r"^[^\x00-\x1f\x7f\u2028\u2029]*\Z"


class AssistantLeadDetails(BaseConstrainedTypedString):
    """
    What the customer wants from a manager as the assistant passes it to
    create_lead (a banquet, a group stay, an order): 1 to 1000 characters,
    no control characters except line breaks and tabs.

    Example:
        details = AssistantLeadDetails("Banquet for 30 guests, Georgian menu")
    """

    min_length = 1
    max_length = 1000
    pattern = r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f]*\Z"


class BookingCalendarFileName(BaseConstrainedTypedString):
    """
    File name a guest's calendar file is saved under (ASCII, ".ics").

    Example:
        name = BookingCalendarFileName("booking-2026-10-06.ics")
    """

    min_length = 5
    max_length = 80
    pattern = r"^[A-Za-z0-9._-]+\.ics$"


class BookingManageLink(BaseConstrainedTypedString):
    """
    Address of the page where a guest sees, moves or cancels their booking:
    the cabinet's public address and a signed manage token.

    Example:
        link = BookingManageLink("https://app.example.com/r/AQ3x...")
    """

    min_length = 10
    max_length = 512
    pattern = r"^https?://[^\s/]+/r/[A-Za-z0-9_-]+$"


class BookingManageToken(BaseConstrainedTypedString):
    """
    The signed, expiring token of a booking's manage link: which booking of
    which business, the version (start time) it was issued for and until
    when (base64url, no padding).

    Example:
        token = BookingManageToken("AQ3xL8...")
    """

    min_length = 40
    max_length = 120
    pattern = r"^[A-Za-z0-9_-]+$"


class CalendarAuthorizationUrl(BaseConstrainedTypedString):
    """
    Provider consent page an owner opens to connect a calendar.

    Example:
        url = CalendarAuthorizationUrl(
            "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
        )
    """

    min_length = 10
    max_length = 4096
    pattern = r"^https://[^\s/]+(/[^\s]*)?$"


class CalendarRedirectUrl(BaseConstrainedTypedString):
    """
    OAuth redirect URI of this backend registered at the calendar provider.

    Example:
        url = CalendarRedirectUrl(
            "https://api.example.com/v1/integrations/google-calendar/callback"
        )
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


class CalendarReturnUrl(BaseConstrainedTypedString):
    """
    Cabinet page an owner is sent back to after the calendar consent page,
    with the outcome in its query.

    Example:
        url = CalendarReturnUrl(
            "https://app.example.com/b/business_1/channels?calendar=connected"
        )
    """

    min_length = 10
    max_length = 4096
    pattern = r"^https?://[^\s/?#]+(/[^\s]*)?$"


class CalendarSyncErrorSummary(BaseConstrainedTypedString):
    """
    Short reason the last calendar sync failed, without tokens or personal
    data (the provider's error code and HTTP status).

    Example:
        reason = CalendarSyncErrorSummary(
            "Google Calendar event insert returned HTTP 401 (UNAUTHENTICATED)."
        )
    """

    min_length = 1
    max_length = 300
    pattern = r"\S"


class LocalDate(BaseConstrainedTypedString):
    """
    Calendar date in the business time zone, ISO 8601 "YYYY-MM-DD", in the
    years 1900-2199 (dates far outside them only overflow calendar maths).

    Example:
        day = LocalDate("2026-10-05")
    """

    min_length = 10
    max_length = 10
    pattern = r"^(19|20|21)[0-9]{2}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class LocalTimeOfDay(BaseConstrainedTypedString):
    """
    Wall-clock time in the business time zone, 24-hour "HH:MM".

    Example:
        time_of_day = LocalTimeOfDay("19:30")
    """

    min_length = 5
    max_length = 5
    pattern = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


# Keep abc order for all non example types, if possible.
