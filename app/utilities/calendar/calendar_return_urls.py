"""Where the owner lands after Google's consent page: the cabinet's callback page."""

from urllib.parse import urlencode

from app.schemas.typings.bookings.constrained_strings import CalendarReturnUrl
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

# The cabinet page that finishes connecting for the signed-in owner and then
# opens the business's Channels page (?calendar=connected or ?calendar=error).
CABINET_CALLBACK_PATH: str = "/integrations/google-calendar/callback"
CALLBACK_PARAMETERS: tuple[str, ...] = ("code", "state", "error")
# Google's values are short; longer ones are cut.
MAX_CALLBACK_VALUE_LENGTH: int = 512


def build_calendar_completion_url(
    cabinet_base_url: CabinetBaseUrl,
    callback_values: dict[str, str | None],
) -> CalendarReturnUrl:
    """
    {CABINET_BASE_URL}/integrations/google-calendar/callback with Google's
    code, state and error: the cabinet finishes connecting there, behind the
    owner's session, so the consent is tied to the user who started it.
    """

    query: dict[str, str] = {
        name: value.strip()[:MAX_CALLBACK_VALUE_LENGTH]
        for name in CALLBACK_PARAMETERS
        if (value := callback_values.get(name)) is not None and value.strip() != ""
    }
    suffix: str = f"?{urlencode(query)}" if query else ""
    return CalendarReturnUrl(
        f"{str(cabinet_base_url).rstrip('/')}{CABINET_CALLBACK_PATH}{suffix}"
    )
