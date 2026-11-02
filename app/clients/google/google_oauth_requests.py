"""
Google OAuth 2.0 (web server flow with PKCE, RFC 7636 S256): the consent
link and the forms of the token endpoint.
"""

from urllib.parse import urlencode

from app.schemas.typings.bookings.constrained_strings import (
    CalendarAuthorizationUrl,
    CalendarRedirectUrl,
)
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarCodeChallenge,
    CalendarCodeVerifier,
    CalendarRefreshToken,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

GOOGLE_AUTHORIZATION_ENDPOINT: str = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT: str = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_ENDPOINT: str = "https://oauth2.googleapis.com/revoke"
# Least privilege: create, change and delete events (bookings mirrored),
# and read calendars (the list to link a resource to, and their free/busy).
GOOGLE_CALENDAR_SCOPES: str = (
    "https://www.googleapis.com/auth/calendar.events "
    "https://www.googleapis.com/auth/calendar.readonly"
)
PKCE_METHOD: str = "S256"


def consent_url(
    client_id: PlatformIdentifier,
    redirect_url: CalendarRedirectUrl,
    state: CalendarAuthorizationState,
    code_challenge: CalendarCodeChallenge,
) -> CalendarAuthorizationUrl:
    """Offline access to calendar events, the state and the PKCE challenge."""

    query: str = urlencode(
        {
            "client_id": str(client_id),
            "redirect_uri": str(redirect_url),
            "response_type": "code",
            "scope": GOOGLE_CALENDAR_SCOPES,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": str(state),
            "code_challenge": str(code_challenge),
            "code_challenge_method": PKCE_METHOD,
        }
    )
    return CalendarAuthorizationUrl(f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}")


def code_exchange_form(
    code: CalendarAuthorizationCode,
    client_id: PlatformIdentifier,
    client_secret: PlatformSecret,
    redirect_url: CalendarRedirectUrl,
    code_verifier: CalendarCodeVerifier | None,
) -> dict[str, str]:
    """The code exchange; the verifier proves the same flow asked for the code."""

    form: dict[str, str] = {
        "code": str(code),
        "client_id": str(client_id),
        "client_secret": str(client_secret),
        "redirect_uri": str(redirect_url),
        "grant_type": "authorization_code",
    }
    if code_verifier is not None:
        form["code_verifier"] = str(code_verifier)
    return form


def refresh_form(
    refresh_token: CalendarRefreshToken,
    client_id: PlatformIdentifier,
    client_secret: PlatformSecret,
) -> dict[str, str]:
    return {
        "refresh_token": str(refresh_token),
        "client_id": str(client_id),
        "client_secret": str(client_secret),
        "grant_type": "refresh_token",
    }
