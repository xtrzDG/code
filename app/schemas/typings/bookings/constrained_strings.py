"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


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
