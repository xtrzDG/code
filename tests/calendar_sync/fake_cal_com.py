"""
A fake Cal.com API v2 behind an httpx MockTransport: event types and
bookings by API key, every request recorded; a key can be refused, the
service can be made slow (the client's read times out).
"""

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.adapters.booking_systems.cal_com_booking_system_adapter import (
    CalComBookingSystemAdapter,
)
from app.clients.cal_com.cal_com_client import CalComClient

type JsonObject = dict[str, Any]

GOOD_KEY: str = "cal_test_key_0000"


@dataclass
class FakeCalCom:
    """The account of `GOOD_KEY`: its event types and their bookings."""

    event_types: dict[str, str] = field(default_factory=lambda: {"1203845": "Haircut"})
    bookings: list[JsonObject] = field(default_factory=list[JsonObject])
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])
    is_slow: bool = False
    created: list[JsonObject] = field(default_factory=list[JsonObject])

    def book(self, start: str, end: str, status: str = "accepted") -> None:
        self.bookings.append(
            {
                "uid": f"uid-{len(self.bookings)}",
                "start": start,
                "end": end,
                "status": status,
            }
        )

    def client(self) -> CalComClient:
        return CalComClient(transport=httpx.MockTransport(self.handle))

    def adapter(self) -> CalComBookingSystemAdapter:
        return CalComBookingSystemAdapter(self.client())

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.is_slow:
            raise httpx.ReadTimeout("slow", request=request)
        if request.headers.get("Authorization") != f"Bearer {GOOD_KEY}":
            return httpx.Response(401, json={"status": "error"})

        path: str = request.url.path.removeprefix("/v2")
        if path.startswith("/event-types/"):
            title = self.event_types.get(path.rsplit("/", 1)[1])
            if title is None:
                return httpx.Response(404, json={"status": "error"})
            return success({"id": int(path.rsplit("/", 1)[1]), "title": title})
        if path == "/bookings" and request.method == "GET":
            skip, take = (
                int(request.url.params["skip"]),
                int(request.url.params["take"]),
            )
            return success(self.bookings[skip : skip + take])
        if path == "/bookings" and request.method == "POST":
            body: JsonObject = json.loads(request.content)
            self.created.append(body)
            return success({"uid": f"created-{len(self.created)}"})
        if path.endswith("/cancel"):
            uid = path.split("/")[2]
            gone = uid.startswith("gone")
            return (
                httpx.Response(404, json={"status": "error"}) if gone else success({})
            )
        return httpx.Response(400, json={"status": "error"})


def success(data: object) -> httpx.Response:
    return httpx.Response(200, json={"status": "success", "data": data})
