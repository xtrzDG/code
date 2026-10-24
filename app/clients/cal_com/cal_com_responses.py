"""
Reading Cal.com API v2 answers: the {"status", "data"} envelope, errors
mapped to the reasons the cabinet explains (never the key), event types
and bookings.
"""

from datetime import datetime
from typing import cast

import httpx

from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError

ACCESS_DENIED_STATUSES: frozenset[int] = frozenset({401, 403})
GONE_STATUSES: frozenset[int] = frozenset({404, 410})
# Bookings that take their time: confirmed, or waiting for confirmation.
BUSY_BOOKING_STATUSES: frozenset[str] = frozenset({"accepted", "pending"})


def read_data(response: httpx.Response, operation: str) -> object:
    """The `data` of a successful answer; the reason of a failed one."""

    status: int = response.status_code
    if status in ACCESS_DENIED_STATUSES:
        raise BusyTimeSourceError(
            f"Cal.com refused the API key ({operation}: HTTP {status}).",
            CalendarSyncProblem.ACCESS_DENIED,
        )
    if status in GONE_STATUSES:
        raise BusyTimeSourceError(
            f"Cal.com does not know it ({operation}: HTTP {status}).",
            CalendarSyncProblem.NOT_FOUND,
        )
    if status >= 400:
        raise BusyTimeSourceError(
            f"Cal.com answered HTTP {status} ({operation}).",
            CalendarSyncProblem.PROVIDER_ERROR,
        )

    try:
        payload: object = response.json()
    except ValueError as error:
        raise BusyTimeSourceError(
            f"Cal.com answered something unreadable ({operation}).",
            CalendarSyncProblem.PROVIDER_ERROR,
        ) from error

    envelope: dict[str, object] = read_object(payload)
    if envelope.get("status") != "success":
        raise BusyTimeSourceError(
            f"Cal.com did not confirm success ({operation}).",
            CalendarSyncProblem.PROVIDER_ERROR,
        )

    return envelope.get("data")


def read_object(data: object) -> dict[str, object]:
    return cast(dict[str, object], data) if isinstance(data, dict) else {}


def read_list(data: object) -> list[object]:
    return cast(list[object], data) if isinstance(data, list) else []


def read_text(fields: dict[str, object], name: str) -> str | None:
    value: object = fields.get(name)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)

    return value.strip() if isinstance(value, str) and value.strip() else None


def read_instant(fields: dict[str, object], name: str) -> int | None:
    """An ISO 8601 instant ("2026-10-10T09:00:00.000Z") in UTC seconds."""

    value: object = fields.get(name)
    if not isinstance(value, str):
        return None

    try:
        moment: datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return int(moment.timestamp()) if moment.tzinfo is not None else None


def is_busy_booking(fields: dict[str, object]) -> bool:
    status: object = fields.get("status")
    return isinstance(status, str) and status.lower() in BUSY_BOOKING_STATUSES
