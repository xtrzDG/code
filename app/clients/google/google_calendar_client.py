"""
Google OAuth 2.0 (web server flow with PKCE) and Google Calendar API v3
over httpx.
"""

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
from app.clients.google.google_oauth_requests import (
    GOOGLE_CALENDAR_SCOPES,
    GOOGLE_REVOKE_ENDPOINT,
    GOOGLE_TOKEN_ENDPOINT,
    code_exchange_form,
    consent_url,
    refresh_form,
)
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
    CalendarCodeChallenge,
    CalendarCodeVerifier,
    CalendarDisplayName,
    CalendarEventId,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

# The scopes stay importable from here (the consent asks for them).
__all__ = ["GOOGLE_CALENDAR_SCOPES", "GoogleCalendarClient"]
GONE_STATUS_CODES: frozenset[int] = frozenset({404, 410})
MAX_CALENDAR_NAME_LENGTH: int = 200


class GoogleCalendarClient(GoogleCalendarClientContract):
    """
    Minimal Google client: consent URL with offline access and a PKCE
    challenge, code exchange with its verifier, token refresh and
    revocation, the calendar's title, event insert, patch and delete, and
    availability: the account's calendars and a calendar's free/busy (these
    two raise BusyTimeSourceError with the reason).

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
        code_challenge: CalendarCodeChallenge,
    ) -> CalendarAuthorizationUrl:
        client_id, _, redirect_url = self._require_credentials()
        return consent_url(client_id, redirect_url, state, code_challenge)

    def exchange_code(
        self,
        code: CalendarAuthorizationCode,
        code_verifier: CalendarCodeVerifier | None,
    ) -> CalendarTokenGrant:
        client_id, client_secret, redirect_url = self._require_credentials()
        form = code_exchange_form(
            code, client_id, client_secret, redirect_url, code_verifier
        )
        return parse_token_grant(
            self._http.post_form(
                GOOGLE_TOKEN_ENDPOINT, form, "Google authorization code exchange"
            )
        )

    def refresh_access_token(
        self,
        refresh_token: CalendarRefreshToken,
    ) -> CalendarTokenGrant:
        client_id, client_secret, _ = self._require_credentials()
        form = refresh_form(refresh_token, client_id, client_secret)
        return parse_token_grant(
            self._http.post_form(GOOGLE_TOKEN_ENDPOINT, form, "Google access token refresh")
        )

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

    def _require_credentials(
        self,
    ) -> tuple[PlatformIdentifier, PlatformSecret, CalendarRedirectUrl]:
        if (
            self._client_id is None
            or self._client_secret is None
            or self._redirect_url is None
        ):
            raise ExternalServiceError(
                "Google Calendar is not configured (GOOGLE_OAUTH_CLIENT_ID, "
                "GOOGLE_OAUTH_CLIENT_SECRET and APP_BASE_URL are required)."
            )

        return self._client_id, self._client_secret, self._redirect_url
