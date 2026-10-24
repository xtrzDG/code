"""
A fake Cal.com API v2 behind an httpx MockTransport: event types and
bookings by API key, every request recorded; a key can be refused, the
service can be made slow (the client's read times out) or fail its writes.
A booking written to it joins its bookings (with its metadata) and a
cancellation cancels it there.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
    cancelled: list[str] = field(default_factory=list[str])
    refuses_writes: bool = False

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
            return self.create(json.loads(request.content))
        if path.endswith("/cancel"):
            uid = path.split("/")[2]
            if uid.startswith("gone"):
                return httpx.Response(404, json={"status": "error"})
            self.cancelled.append(uid)
            for booking in self.bookings:
                if booking["uid"] == uid:
                    booking["status"] = "cancelled"
            return success({})
        return httpx.Response(400, json={"status": "error"})

    def create(self, body: JsonObject) -> httpx.Response:
        if self.refuses_writes:
            return httpx.Response(400, json={"status": "error"})

        self.created.append(body)
        uid = f"created-{len(self.created)}"
        start = datetime.fromisoformat(str(body["start"]).replace("Z", "+00:00"))
        end = start + timedelta(minutes=int(body["lengthInMinutes"]))
        self.bookings.append(
            {
                "uid": uid,
                "start": body["start"],
                "end": end.isoformat().replace("+00:00", "Z"),
                "status": "accepted",
                "metadata": body.get("metadata", {}),
            }
        )
        return success({"uid": uid})

    def active_created(self) -> list[str]:
        """The platform's bookings there that are not cancelled."""

        return [
            str(booking["uid"])
            for booking in self.bookings
            if str(booking["uid"]).startswith("created-")
            and booking["status"] == "accepted"
        ]


def success(data: object) -> httpx.Response:
    return httpx.Response(200, json={"status": "success", "data": data})
