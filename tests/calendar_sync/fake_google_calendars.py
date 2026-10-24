"""
FakeGoogle with the availability side of Google Calendar: free/busy
queries answered from busy periods per calendar, and the account's
calendar list. Either can be made to fail with an HTTP status.
"""

import json
from typing import Any

import httpx

from tests.operations.fake_google import FakeGoogle

type JsonObject = dict[str, Any]

PRIMARY_CALENDAR: str = "owner@example.com"
TEAM_CALENDAR: str = "team-room@group.calendar.google.com"


class FakeGoogleCalendars(FakeGoogle):
    """`busy` maps a calendar id to its (start, end) RFC 3339 pairs."""

    def __init__(self) -> None:
        super().__init__()
        self.busy: dict[str, list[tuple[str, str]]] = {}
        self.calendars: list[JsonObject] = [
            {"id": TEAM_CALENDAR, "summary": "Room 1", "accessRole": "reader"},
            {
                "id": PRIMARY_CALENDAR,
                "summary": PRIMARY_CALENDAR,
                "primary": True,
                "accessRole": "owner",
            },
        ]
        self.free_busy_status: int | None = None
        self.calendar_list_status: int | None = None
        self.free_busy_queries: list[JsonObject] = []

    def _handle_calendar(self, request: httpx.Request) -> httpx.Response:
        path: str = request.url.path
        if path.endswith("/freeBusy"):
            return self._free_busy(request)
        if path.endswith("/users/me/calendarList"):
            if self.calendar_list_status is not None:
                return httpx.Response(self.calendar_list_status, json={})
            return httpx.Response(200, json={"items": self.calendars})

        return super()._handle_calendar(request)

    def _free_busy(self, request: httpx.Request) -> httpx.Response:
        query: JsonObject = json.loads(request.content)
        self.free_busy_queries.append(query)
        if self.free_busy_status is not None:
            return httpx.Response(self.free_busy_status, json={})

        calendars: JsonObject = {}
        for item in query["items"]:
            calendar_id: str = str(item["id"])
            if calendar_id in self.busy or calendar_id == "primary":
                calendars[calendar_id] = {
                    "busy": [
                        {"start": start, "end": end}
                        for start, end in self.busy.get(calendar_id, [])
                    ]
                }
            else:
                calendars[calendar_id] = {
                    "errors": [{"domain": "global", "reason": "notFound"}]
                }
        return httpx.Response(
            200, json={"kind": "calendar#freeBusy", "calendars": calendars}
        )
