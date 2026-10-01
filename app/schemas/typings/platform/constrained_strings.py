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


class EnvironmentVariableName(BaseConstrainedTypedString):
    """
    Name of a server setting read from the environment, e.g. "APP_BASE_URL";
    reported when a feature cannot work because the setting is missing.

    Example:
        name = EnvironmentVariableName("ELEVENLABS_API_KEY")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Z][A-Z0-9_]*$"


class ErrorReasonCode(BaseConstrainedTypedString):
    """
    Stable machine-readable code of one reason an API request was refused,
    e.g. "dpa" or "menu_link_unreachable"; clients branch on it instead of
    the English message.

    Example:
        code = ErrorReasonCode("profile_gaps")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class ErrorReasonDetail(BaseConstrainedTypedString):
    """
    One machine value that qualifies a refusal reason: a gap kind, a status,
    a document version, the name of a missing setting or a media type.

    Example:
        detail = ErrorReasonDetail("no_opening_hours")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[A-Za-z0-9][A-Za-z0-9_.:/+\-]*$"


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
