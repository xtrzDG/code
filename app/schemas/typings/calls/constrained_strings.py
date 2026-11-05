"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CallCollectedDate(BaseConstrainedTypedString):
    """
    The date of a booking a caller asked for, as the voice platform's
    evaluation of the call read it from the conversation (YYYY-MM-DD).

    Example:
        booking_date = CallCollectedDate("2026-10-24")
    """

    min_length = 10
    max_length = 10
    pattern = r"^\d{4}-\d{2}-\d{2}$"


class CallCollectedTime(BaseConstrainedTypedString):
    """
    The time of a booking a caller asked for, as the voice platform's
    evaluation of the call read it (HH:MM, 24 hours).

    Example:
        booking_time = CallCollectedTime("19:30")
    """

    min_length = 5
    max_length = 5
    pattern = r"^([01]\d|2[0-3]):[0-5]\d$"


class CallSummaryText(BaseConstrainedTypedString):
    """
    A short summary of a phone call for staff, in one language: what the
    caller wanted and how it ended, in one to three sentences.

    Example:
        summary = CallSummaryText("Asked for a table for four tomorrow at 8 pm.")
    """

    min_length = 1
    max_length = 600


# Keep abc order for all non example types, if possible.
