import json
from collections.abc import Callable
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.clients.google.google_calendar_client import (
    GOOGLE_CALENDAR_CALLBACK_PATH,
    GoogleCalendarClient,
    build_google_calendar_redirect_url,
)
from app.schemas.dto.operations.calendar_connection import CalendarEventDraft
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarEventDescription,
    CalendarEventId,
    CalendarEventTitle,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import (
    TimezoneName,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.operations.fake_google import REDIRECT_URL, FakeGoogle

DRAFT = CalendarEventDraft(
    title=CalendarEventTitle("Booking: Nino, guests: 4"),
    description=CalendarEventDescription("Table 4"),
    starts_at=BookingStartsAtUnixSeconds(
        int(datetime.fromisoformat("2026-10-06T19:00:00+04:00").timestamp())
    ),
    ends_at=BookingEndsAtUnixSeconds(
        int(datetime.fromisoformat("2026-10-06T21:00:00+04:00").timestamp())
    ),
    timezone=TimezoneName("Asia/Tbilisi"),
)
ACCESS = CalendarAccessToken("access-xyz")


class TestGoogleCalendarClient:
    def test_authorization_url_asks_for_offline_calendar_events_access(self) -> None:
        url = (
            FakeGoogle()
            .client()
            .build_authorization_url(CalendarAuthorizationState("state-123"))
        )

        parts = urlsplit(str(url))
        query = {key: values[0] for key, values in parse_qs(parts.query).items()}
        assert f"{parts.scheme}://{parts.netloc}{parts.path}" == (
            "https://accounts.google.com/o/oauth2/v2/auth"
        )
        assert query == {
            "client_id": "client-123.apps.googleusercontent.com",
            "redirect_uri": str(REDIRECT_URL),
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar.events",
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": "state-123",
        }

    def test_code_exchange_and_refresh_post_forms_to_the_token_endpoint(self) -> None:
        google = FakeGoogle()
        client = google.client()

        grant = client.exchange_code(CalendarAuthorizationCode("good-code"))
        refreshed = client.refresh_access_token(CalendarRefreshToken("refresh-initial"))

        assert (grant.access_token, grant.refresh_token, grant.expires_in) == (
            "access-initial",
            "refresh-initial",
            3599,
        )
        assert refreshed.refresh_token is None
        exchange, refresh = google.requests
        assert str(exchange.url) == "https://oauth2.googleapis.com/token"
        assert exchange.headers["content-type"] == "application/x-www-form-urlencoded"
        assert google.form(exchange) == {
            "code": "good-code",
            "client_id": "client-123.apps.googleusercontent.com",
            "client_secret": "client-secret",
            "redirect_uri": str(REDIRECT_URL),
            "grant_type": "authorization_code",
        }
        assert google.form(refresh)["grant_type"] == "refresh_token"

    def test_google_errors_never_leak_tokens(self) -> None:
        client = FakeGoogle().client()

        with pytest.raises(ExternalServiceError) as error:
            client.refresh_access_token(CalendarRefreshToken("revoked-secret-token"))

        assert "invalid_grant" in str(error.value)
        assert "revoked-secret-token" not in str(error.value)

    def test_event_insert_patch_and_delete(self) -> None:
        google = FakeGoogle()
        client = google.client()
        shared_calendar = ExternalCalendarId("team@group.calendar.google.com")

        event_id = client.insert_event(ACCESS, shared_calendar, DRAFT)
        client.patch_event(ACCESS, shared_calendar, event_id, DRAFT)
        client.delete_event(ACCESS, shared_calendar, event_id)
        client.delete_event(ACCESS, shared_calendar, event_id)

        insert, patch, delete, delete_again = google.requests
        assert insert.method == "POST"
        assert insert.url.raw_path.decode() == (
            "/calendar/v3/calendars/team%40group.calendar.google.com/events"
        )
        assert insert.headers["authorization"] == "Bearer access-xyz"
        assert json.loads(insert.content) == {
            "summary": "Booking: Nino, guests: 4",
            "description": "Table 4",
            "start": {"dateTime": "2026-10-06T15:00:00Z", "timeZone": "Asia/Tbilisi"},
            "end": {"dateTime": "2026-10-06T17:00:00Z", "timeZone": "Asia/Tbilisi"},
        }
        assert (patch.method, delete.method) == ("PATCH", "DELETE")
        assert patch.url.raw_path.decode().endswith(f"/events/{event_id}")
        assert delete_again.method == "DELETE"
        assert google.events == {}

    def test_transport_server_and_payload_failures(self) -> None:
        def broken(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("unreachable", request=request)

        def no_id(request: httpx.Request) -> httpx.Response:
            del request
            return httpx.Response(200, json={"status": "confirmed"})

        def not_json(request: httpx.Request) -> httpx.Response:
            del request
            return httpx.Response(200, content=b"<html>")

        google = FakeGoogle()
        google.failure_status = 500

        with pytest.raises(ExternalServiceError, match="ConnectError"):
            client_with(broken).insert_event(
                ACCESS, ExternalCalendarId("primary"), DRAFT
            )

        with pytest.raises(ExternalServiceError, match="without id"):
            client_with(no_id).insert_event(
                ACCESS, ExternalCalendarId("primary"), DRAFT
            )

        with pytest.raises(ExternalServiceError, match="unexpected payload"):
            client_with(not_json).exchange_code(CalendarAuthorizationCode("good-code"))

        with pytest.raises(ExternalServiceError, match="HTTP 500 \\(UNAVAILABLE\\)"):
            google.client().delete_event(
                ACCESS, ExternalCalendarId("primary"), CalendarEventId("event1")
            )

    def test_calendar_title_comes_from_an_events_listing(self) -> None:
        google = FakeGoogle()

        title = google.client().get_calendar_name(ACCESS, ExternalCalendarId("primary"))

        assert title == "owner@example.com"
        [request] = google.requests
        assert request.method == "GET"
        assert request.url.path == "/calendar/v3/calendars/primary/events"
        assert request.url.params["fields"] == "summary"
        assert request.headers["authorization"] == "Bearer access-xyz"

        google.calendar_name = None
        assert (
            google.client().get_calendar_name(ACCESS, ExternalCalendarId("p")) is None
        )
        google.failure_status = 401
        with pytest.raises(ExternalServiceError, match="HTTP 401"):
            google.client().get_calendar_name(ACCESS, ExternalCalendarId("primary"))

    def test_missing_configuration(self) -> None:
        unconfigured = GoogleCalendarClient(
            client_id=PlatformIdentifier("client"),
            client_secret=None,
            redirect_url=None,
        )

        with pytest.raises(ExternalServiceError, match="not configured"):
            unconfigured.build_authorization_url(CalendarAuthorizationState("s"))

        assert not unconfigured.is_configured()
        assert FakeGoogle().client().is_configured()

        assert build_google_calendar_redirect_url(None) is None
        assert build_google_calendar_redirect_url(
            PublicBaseUrl("https://api.example.com/")
        ) == (f"https://api.example.com{GOOGLE_CALENDAR_CALLBACK_PATH}")


def client_with(
    handler: Callable[[httpx.Request], httpx.Response],
) -> GoogleCalendarClient:
    return GoogleCalendarClient(
        client_id=PlatformIdentifier("client"),
        client_secret=PlatformSecret("secret"),
        redirect_url=REDIRECT_URL,
        transport=httpx.MockTransport(handler),
    )
