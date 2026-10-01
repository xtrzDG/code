"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class JobName(BaseConstrainedTypedString):
    """
    Stable snake-case name of a background job, e.g. "purge_expired_recordings".

    Example:
        name = JobName("send_booking_reminders")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


# Keep abc order for all non example types, if possible.
