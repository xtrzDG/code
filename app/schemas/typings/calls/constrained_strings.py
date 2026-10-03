"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


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
