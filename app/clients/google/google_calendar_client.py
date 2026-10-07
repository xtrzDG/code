"""Google OAuth 2.0 (web server flow) and Google Calendar API v3 over httpx."""

from urllib.parse import urlencode

import httpx

from app.clients.google.google_api_responses import (
    ensure_success,
    parse_token_grant,
    read_json_object,
)
from app.clients.google.google_availability import (
    CALENDAR_LIST_PARAMS,
    CALENDAR_LIST_URL,
    FREE_BUSY_URL,
    free_busy_body,
    read_busy_periods,
    read_calendar_entries,
)
from app.clients.google.google_calendar_requests import (
    bearer,
    event_body,
    event_url,
    events_url,
)
from app.clients.google.google_http import GoogleHttp
from app.contracts.operations import GoogleCalendarClientContract
from app.schemas.dto.calendar_sync.busy_reads import (
    BusyPeriod,
    BusyWindow,
    GoogleCalendarEntry,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarEventDraft,
    CalendarTokenGrant,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.constrained_strings import (
    CalendarAuthorizationUrl,
    CalendarRedirectUrl,
)
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarDisplayName,
    CalendarEventId,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
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
GONE_STATUS_CODES: frozenset[int] = frozenset({404, 410})
MAX_CALENDAR_NAME_LENGTH: int = 200


class GoogleCalendarClient(GoogleCalendarClientContract):
    """
    Minimal Google client: consent URL with offline access, code exchange,
    token refresh and revocation, the calendar's title, event insert, patch
    and delete, and availability: the account's calendars and a calendar's
    free/busy (these two raise BusyTimeSourceError with the reason).

    Missing credentials (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET,
    APP_BASE_URL) make every call raise ExternalServiceError, as do network
    and HTTP errors. Error messages never contain tokens.
    """

    def __init__(
        self,
        client_id: PlatformIdentifier | None,
        client_secret: PlatformSecret | None,
        redirect_url: CalendarRedirectUrl | None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client_id: PlatformIdentifier | None = client_id
        self._client_secret: PlatformSecret | None = client_secret
        self._redirect_url: CalendarRedirectUrl | None = redirect_url
        self._http: GoogleHttp = GoogleHttp(transport)

    def is_configured(self) -> bool:
        return (
            self._client_id is not None
            and self._client_secret is not None
            and self._redirect_url is not None
        )

    def build_authorization_url(
        self,
        state: CalendarAuthorizationState,
    ) -> CalendarAuthorizationUrl:
        client_id, _, redirect_url = self._require_credentials()
        query: str = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_url,
                "response_type": "code",
                "scope": GOOGLE_CALENDAR_SCOPES,
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "state": str(state),
            }
        )
        return CalendarAuthorizationUrl(f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}")

    def exchange_code(self, code: CalendarAuthorizationCode) -> CalendarTokenGrant:
        client_id, client_secret, redirect_url = self._require_credentials()
        payload: dict[str, object] = self._http.post_form(
            GOOGLE_TOKEN_ENDPOINT,
            {
                "code": str(code),
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_url,
                "grant_type": "authorization_code",
            },
            "Google authorization code exchange",
        )
        return parse_token_grant(payload)

    def refresh_access_token(
        self,
        refresh_token: CalendarRefreshToken,
    ) -> CalendarTokenGrant:
        client_id, client_secret, _ = self._require_credentials()
        payload: dict[str, object] = self._http.post_form(
            GOOGLE_TOKEN_ENDPOINT,
            {
                "refresh_token": str(refresh_token),
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
            "Google access token refresh",
        )
        return parse_token_grant(payload)

    def revoke_token(self, refresh_token: CalendarRefreshToken) -> None:
        response: httpx.Response = self._http.send(
            "POST",
            GOOGLE_REVOKE_ENDPOINT,
            "Google token revocation",
            data={"token": str(refresh_token)},
        )
        ensure_success(response, "Google token revocation")

    def get_calendar_name(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
    ) -> CalendarDisplayName | None:
        # The events scope cannot read calendar metadata, but an events list
        # carries the calendar's title ("summary"); one field, no events.
        response: httpx.Response = self._http.send(
            "GET",
            events_url(calendar_id),
            "Google Calendar title lookup",
            headers=bearer(access_token),
            params={"maxResults": "1", "fields": "summary"},
        )
        ensure_success(response, "Google Calendar title lookup")
        summary: object = read_json_object(
            response, "Google Calendar title lookup"
        ).get("summary")
        if not isinstance(summary, str) or summary.strip() == "":
            return None

        return CalendarDisplayName(summary.strip()[:MAX_CALENDAR_NAME_LENGTH])

    def insert_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event: CalendarEventDraft,
    ) -> CalendarEventId:
        response: httpx.Response = self._http.send(
            "POST",
            events_url(calendar_id),
            "Google Calendar event insert",
            headers=bearer(access_token),
            json=event_body(event),
        )
        ensure_success(response, "Google Calendar event insert")
        payload: dict[str, object] = read_json_object(
            response, "Google Calendar event insert"
        )
        event_id: object = payload.get("id")
        if not isinstance(event_id, str) or event_id == "":
            raise ExternalServiceError("Google Calendar returned an event without id.")

        return CalendarEventId(event_id)

    def patch_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
        event: CalendarEventDraft,
    ) -> None:
        response: httpx.Response = self._http.send(
            "PATCH",
            event_url(calendar_id, event_id),
            "Google Calendar event update",
            headers=bearer(access_token),
            json=event_body(event),
        )
        ensure_success(response, "Google Calendar event update")

    def delete_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
    ) -> None:
        response: httpx.Response = self._http.send(
            "DELETE",
            event_url(calendar_id, event_id),
            "Google Calendar event delete",
            headers=bearer(access_token),
        )
        if response.status_code in GONE_STATUS_CODES:
            return

        ensure_success(response, "Google Calendar event delete")

    def query_free_busy(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        window: BusyWindow,
        timeout: BusyTimeFetchSeconds,
    ) -> list[BusyPeriod]:
        response: httpx.Response = self._http.read_availability(
            "POST",
            FREE_BUSY_URL,
            access_token,
            timeout,
            json=free_busy_body(calendar_id, window),
        )
        return read_busy_periods(response, calendar_id)

    def list_calendars(
        self,
        access_token: CalendarAccessToken,
        timeout: BusyTimeFetchSeconds,
    ) -> list[GoogleCalendarEntry]:
        response: httpx.Response = self._http.read_availability(
            "GET",
            CALENDAR_LIST_URL,
            access_token,
            timeout,
            params=CALENDAR_LIST_PARAMS,
        )
        return read_calendar_entries(response)

    def _require_credentials(self) -> tuple[str, str, str]:
        if (
            self._client_id is None
            or self._client_secret is None
            or self._redirect_url is None
        ):
            raise ExternalServiceError(
                "Google Calendar is not configured (GOOGLE_OAUTH_CLIENT_ID, "
                "GOOGLE_OAUTH_CLIENT_SECRET and APP_BASE_URL are required)."
            )

        return str(self._client_id), str(self._client_secret), str(self._redirect_url)
