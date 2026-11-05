"""Keep abc order."""

from base_typed_string import BaseTypedString


class RestoreCheckProblem(BaseTypedString):
    """
    One check of a restore drill that failed, as an English sentence for
    the log and Sentry ("workshop.bookings: 120 rows restored, 121 dumped").
    Names tables and counts only, never row contents.
    """


# Keep abc order for all non example types, if possible.
