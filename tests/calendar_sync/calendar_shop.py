"""
A restaurant with one table, through the real application: its owner, the
table's calendar paths, the busy times outside the platform (iCal feeds,
Cal.com, Google) as fakes, and the free slots of a day.
"""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from httpx2 import Response

from app.containers.app import AppContainer
from app.gateways.http.operations.google_calendar_routes import (
    GOOGLE_CALENDAR_COMPLETE_PATH,
)
from tests.calendar_sync.calendar_edges import CalendarEdges
from tests.calendar_sync.fake_google_calendars import FakeGoogleCalendars
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.journeys import sign_in_and_create_restaurant
from tests.e2e.workshop_container import replace_provider

type JsonObject = dict[str, Any]

# Tbilisi (UTC+4): the workshop starts on Monday 2026-10-05 at 12:00 there;
# the table takes hour-long bookings every half hour from 12:00 to 17:00.
DAY: str = "2026-10-06"
OPEN_ALL_WEEK: list[JsonObject] = [
    {"weekday": weekday, "opens_at": 720, "closes_at": 1020} for weekday in range(1, 8)
]
FEED_URL: str = "https://www.airbnb.com/calendar/ical/1203845.ics?s=test-feed-0000"
OTHER_FEED_URL: str = "https://admin.booking.com/hotel/ical/42.ics?t=test-feed-0001"


@dataclass
class CalendarShop:
    workshop: Workshop
    edges: CalendarEdges
    google: FakeGoogleCalendars
    token: str
    business_id: str
    resource_id: str

    @property
    def client(self) -> TestClient:
        return self.workshop.client

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.token)

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"

    @property
    def calendar(self) -> str:
        return f"{self.base}/resources/{self.resource_id}/calendar"

    def get(self, path: str, **params: str) -> Response:
        return self.client.get(path, params=params, headers=self.headers)

    def post(self, path: str, body: JsonObject | None = None) -> Response:
        return self.client.post(path, json=body or {}, headers=self.headers)

    def put(self, path: str, body: JsonObject) -> Response:
        return self.client.put(path, json=body, headers=self.headers)

    def delete(self, path: str) -> Response:
        return self.client.delete(path, headers=self.headers)

    def view(self) -> JsonObject:
        response = self.get(self.calendar)
        assert response.status_code == 200, response.text
        return dict(response.json())

    def free_times(self, day: str = DAY) -> list[str]:
        response = self.get(f"{self.base}/availability", date=day, party_size="2")
        assert response.status_code == 200, response.text
        return [str(slot["time"]) for slot in response.json()["slots"]]

    def import_feed(self, url: str = FEED_URL) -> Response:
        return self.post(f"{self.calendar}/ical-imports", {"url": url})

    def connect_google(self) -> None:
        connect = self.get(f"{self.base}/integrations/google-calendar/connect-url")
        assert connect.status_code == 200, connect.text
        query = urlsplit(str(connect.json()["authorization_url"])).query
        completed = self.post(
            GOOGLE_CALENDAR_COMPLETE_PATH,
            {"state": parse_qs(query)["state"][0], "code": "good-code"},
        )
        assert completed.json()["failure"] is None, completed.text

    def book(self, time: str, day: str = DAY) -> Response:
        return self.post(
            f"{self.base}/bookings",
            {
                "contact_name": "Nino",
                "contact_phone_number": "+995 555 11 22 33",
                "date": day,
                "time": time,
                "party_size": 2,
                "resource_id": self.resource_id,
            },
        )


def calendar_ics(*events: str) -> str:
    """A calendar of VEVENT bodies (lines without BEGIN/END)."""

    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Test//Feed//EN",
            *(f"BEGIN:VEVENT\r\n{event}\r\nEND:VEVENT" for event in events),
            "END:VCALENDAR",
            "",
        ]
    )


@contextmanager
def open_calendar_shop() -> Generator[CalendarShop]:
    edges = CalendarEdges()
    google = FakeGoogleCalendars()

    def prepare(container: AppContainer) -> None:
        edges.install(container)
        replace_provider(container.clients.google_calendar_client, google.client())

    workshop = start_workshop(prepare=prepare)
    with workshop.client:
        token, _, business_id = sign_in_and_create_restaurant(workshop)
        table = workshop.client.post(
            f"/v1/businesses/{business_id}/resources",
            json={
                "name": "Window table",
                "capacity": 4,
                "slot_minutes": 60,
                "schedule": OPEN_ALL_WEEK,
            },
            headers=bearer(token),
        )
        assert table.status_code == 201, table.text
        yield CalendarShop(
            workshop=workshop,
            edges=edges,
            google=google,
            token=token,
            business_id=business_id,
            resource_id=str(table.json()["id"]),
        )
