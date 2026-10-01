"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CabinetBaseUrl(BaseConstrainedTypedString):
    """
    Public address of the owner cabinet (the web app), where the backend
    sends owners back after a provider's consent page.

    Example:
        cabinet_url = CabinetBaseUrl("https://app.example.com")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/?#]+(/[^\s?#]*)?$"


class JobName(BaseConstrainedTypedString):
    """
    Stable snake-case name of a background job, e.g. "purge_expired_recordings".

    Example:
        name = JobName("send_booking_reminders")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class PageCursor(BaseConstrainedTypedString):
    """
    Opaque position in a list sorted newest first, returned as `next_cursor`
    and sent back as `cursor` to get the next page.

    Example:
        cursor = PageCursor("MTc5MDg2MTAwODg1MzAwMDpib29raW5nXzE")
    """

    min_length = 1
    max_length = 200
    pattern = r"^[A-Za-z0-9_-]+$"


# Keep abc order for all non example types, if possible.
