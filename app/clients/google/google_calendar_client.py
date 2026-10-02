"""Google OAuth 2.0 (web server flow) and Google Calendar API v3 over httpx."""

from urllib.parse import urlencode

import httpx

from app.clients.google.google_api_responses import (
    ensure_success,
    parse_token_grant,
    read_json_object,
)
from app.clients.google.google_calendar_requests import (
    bearer,
    event_body,
    event_url,
    events_url,
)
from app.contracts.operations import GoogleCalendarClientContract
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
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

GOOGLE_AUTHORIZATION_ENDPOINT: str = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT: str = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_ENDPOINT: str = "https://oauth2.googleapis.com/revoke"
# Least privilege: create, change and delete events only.
GOOGLE_CALENDAR_EVENTS_SCOPE: str = "https://www.googleapis.com/auth/calendar.events"
REQUEST_TIMEOUT_SECONDS: float = 10.0
GONE_STATUS_CODES: frozenset[int] = frozenset({404, 410})
MAX_CALENDAR_NAME_LENGTH: int = 200


class GoogleCalendarClient(GoogleCalendarClientContract):
    """
    Minimal Google client: consent URL with offline access, code exchange,
    token refresh and revocation, the calendar's title, and event insert,
    patch and delete.

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
        self._http_client: httpx.Client = httpx.Client(
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

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
                "scope": GOOGLE_CALENDAR_EVENTS_SCOPE,
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "state": str(state),
            }
        )
        return CalendarAuthorizationUrl(f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}")

    def exchange_code(self, code: CalendarAuthorizationCode) -> CalendarTokenGrant:
        client_id, client_secret, redirect_url = self._require_credentials()
        payload: dict[str, object] = self._post_form(
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
        payload: dict[str, object] = self._post_form(
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
        response: httpx.Response = self._send(
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
        response: httpx.Response = self._send(
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
        response: httpx.Response = self._send(
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
        response: httpx.Response = self._send(
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
        response: httpx.Response = self._send(
            "DELETE",
            event_url(calendar_id, event_id),
            "Google Calendar event delete",
            headers=bearer(access_token),
        )
        if response.status_code in GONE_STATUS_CODES:
            return

        ensure_success(response, "Google Calendar event delete")

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

    def _post_form(
        self,
        url: str,
        form: dict[str, str],
        operation: str,
    ) -> dict[str, object]:
        response: httpx.Response = self._send("POST", url, operation, data=form)
        ensure_success(response, operation)
        return read_json_object(response, operation)

    def _send(
        self,
        method: str,
        url: str,
        operation: str,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            return self._http_client.request(
                method,
                url,
                headers=headers,
                data=data,
                json=json,
                params=params,
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"{operation} failed: {type(error).__name__}."
            ) from error
