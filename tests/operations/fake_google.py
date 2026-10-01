"""In-process stand-in for Google OAuth and Calendar served via MockTransport."""

import json
from urllib.parse import parse_qs, unquote

import httpx

from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.schemas.typings.bookings.constrained_strings import CalendarRedirectUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

REDIRECT_URL: CalendarRedirectUrl = CalendarRedirectUrl(
    "https://api.example.com/v1/integrations/google-calendar/callback"
)


class FakeGoogle:
    """Records requests and keeps calendar events in memory."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.events: dict[str, dict[str, object]] = {}
        self.failure_status: int | None = None
        self.grants_refresh_token: bool = True
        self.refresh_count: int = 0
        self.revoked_tokens: list[str] = []
        self.calendar_name: str | None = "owner@example.com"
        self._next_event_number: int = 1

    def client(self) -> GoogleCalendarClient:
        return GoogleCalendarClient(
            client_id=PlatformIdentifier("client-123.apps.googleusercontent.com"),
            client_secret=PlatformSecret("client-secret"),
            redirect_url=REDIRECT_URL,
            transport=httpx.MockTransport(self.handle),
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.failure_status is not None:
            return httpx.Response(
                self.failure_status, json={"error": {"status": "UNAVAILABLE"}}
            )

        if request.url.host == "oauth2.googleapis.com":
            return self._handle_oauth(request)

        return self._handle_calendar(request)

    def form(self, request: httpx.Request) -> dict[str, str]:
        return {
            key: values[0] for key, values in parse_qs(request.content.decode()).items()
        }

    def _handle_oauth(self, request: httpx.Request) -> httpx.Response:
        form: dict[str, str] = self.form(request)
        if request.url.path == "/revoke":
            self.revoked_tokens.append(form["token"])
            return httpx.Response(200)

        if form.get("grant_type") == "authorization_code":
            if form.get("code") != "good-code":
                return httpx.Response(400, json={"error": "invalid_grant"})

            body: dict[str, object] = {
                "access_token": "access-initial",
                "expires_in": 3599,
                "token_type": "Bearer",
            }
            if self.grants_refresh_token:
                body["refresh_token"] = "refresh-initial"

            return httpx.Response(200, json=body)

        if form.get("refresh_token") != "refresh-initial":
            return httpx.Response(
                400,
                json={
                    "error": "invalid_grant",
                    "error_description": "Token has been expired or revoked.",
                },
            )

        self.refresh_count += 1
        return httpx.Response(
            200,
            json={
                "access_token": f"access-refreshed-{self.refresh_count}",
                "expires_in": 3599,
                "token_type": "Bearer",
            },
        )

    def _handle_calendar(self, request: httpx.Request) -> httpx.Response:
        parts: list[str] = request.url.raw_path.decode().split("?")[0].split("/")
        # /calendar/v3/calendars/{calendar_id}/events[/{event_id}]
        event_id: str | None = unquote(parts[6]) if len(parts) > 6 else None
        if request.method == "GET" and event_id is None:
            listing: dict[str, object] = {"items": []}
            if self.calendar_name is not None:
                listing["summary"] = self.calendar_name
            return httpx.Response(200, json=listing)

        if request.method == "POST":
            new_id = f"event{self._next_event_number}"
            self._next_event_number += 1
            self.events[new_id] = json.loads(request.content)
            return httpx.Response(200, json={"id": new_id, "status": "confirmed"})

        if event_id is None or event_id not in self.events:
            return httpx.Response(410, json={"error": {"status": "GONE"}})

        if request.method == "PATCH":
            self.events[event_id] = json.loads(request.content)
            return httpx.Response(200, json={"id": event_id})

        del self.events[event_id]
        return httpx.Response(204)
