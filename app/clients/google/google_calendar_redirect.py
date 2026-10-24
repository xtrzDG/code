"""The OAuth redirect address of this backend for Google Calendar."""

from app.schemas.typings.bookings.constrained_strings import CalendarRedirectUrl
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl

GOOGLE_CALENDAR_CALLBACK_PATH: str = "/v1/integrations/google-calendar/callback"


def build_google_calendar_redirect_url(
    app_base_url: PublicBaseUrl | None,
) -> CalendarRedirectUrl | None:
    """OAuth redirect URI of this backend (APP_BASE_URL + callback path)."""

    if app_base_url is None:
        return None

    return CalendarRedirectUrl(
        f"{str(app_base_url).rstrip('/')}{GOOGLE_CALENDAR_CALLBACK_PATH}"
    )
