"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class LocalDate(BaseConstrainedTypedString):
    """
    Calendar date in the business time zone, ISO 8601 "YYYY-MM-DD".

    Example:
        day = LocalDate("2026-10-05")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


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
