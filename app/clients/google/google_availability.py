"""
Google Calendar availability: the free/busy query and the account's
calendar list, their request bodies, and their answers read into busy
periods and calendar entries. Failures become `BusyTimeSourceError` with
the reason the cabinet explains (never a token).
"""

from datetime import datetime
from typing import cast

import httpx

from app.clients.google.google_api_responses import (
    describe_google_error,
    read_json_object,
)
from app.clients.google.google_calendar_requests import (
    GOOGLE_CALENDAR_API_BASE_URL,
    format_rfc3339,
)
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import (
    BusyPeriod,
    BusyWindow,
    GoogleCalendarEntry,
)
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.strings import (
    CalendarDisplayName,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.strings import GoogleCalendarAccessRole

FREE_BUSY_URL: str = f"{GOOGLE_CALENDAR_API_BASE_URL}/freeBusy"
CALENDAR_LIST_URL: str = f"{GOOGLE_CALENDAR_API_BASE_URL}/users/me/calendarList"
CALENDAR_LIST_PARAMS: dict[str, str] = {
    # Calendars whose busy times the account may see, at most 250 of them.
    "minAccessRole": "freeBusyReader",
    "maxResults": "250",
    "fields": "items(id,summary,summaryOverride,primary,accessRole)",
}
MAX_CALENDAR_NAME_LENGTH: int = 200
# The account lacks the permission (consent given before calendars were
# read) or lost it: the owner connects Google Calendar again.
RECONNECT_STATUSES: frozenset[int] = frozenset({401, 403})
GONE_STATUSES: frozenset[int] = frozenset({404, 410})


def free_busy_body(
    calendar_id: ExternalCalendarId, window: BusyWindow
) -> dict[str, object]:
    return {
        "timeMin": format_rfc3339(int(window.starts_at)),
        "timeMax": format_rfc3339(int(window.ends_at)),
        "items": [{"id": str(calendar_id)}],
    }


def ensure_readable(response: httpx.Response, operation: str) -> None:
    """Raise the reason a Google answer is an error, if it is one."""

    status: int = response.status_code
    if status < 400:
        return

    summary: str = (
        f"{operation} returned HTTP {status}{describe_google_error(response)}."
    )
    if status in RECONNECT_STATUSES:
        raise BusyTimeSourceError(summary, CalendarSyncProblem.NEEDS_RECONNECT)
    if status in GONE_STATUSES:
        raise BusyTimeSourceError(summary, CalendarSyncProblem.NOT_FOUND)
    raise BusyTimeSourceError(summary, CalendarSyncProblem.PROVIDER_ERROR)


def read_busy_periods(
    response: httpx.Response, calendar_id: ExternalCalendarId
) -> list[BusyPeriod]:
    """The calendar's busy periods of a free/busy answer (calendar errors raise)."""

    ensure_readable(response, "Google free/busy query")
    payload: dict[str, object] = read_json_object(response, "Google free/busy query")
    calendars: object = payload.get("calendars")
    entry: object = (
        cast(dict[str, object], calendars).get(str(calendar_id))
        if isinstance(calendars, dict)
        else None
    )
    if not isinstance(entry, dict):
        raise BusyTimeSourceError(
            "Google free/busy answered without the calendar.",
            CalendarSyncProblem.PROVIDER_ERROR,
        )

    fields: dict[str, object] = cast(dict[str, object], entry)
    raise_calendar_errors(fields.get("errors"))
    busy: object = fields.get("busy")
    if not isinstance(busy, list):
        return []

    return [
        period
        for item in cast(list[object], busy)
        if (period := read_period(item)) is not None
    ]


def raise_calendar_errors(errors: object) -> None:
    """Google names a calendar it cannot read in `errors` (notFound, ...)."""

    if not isinstance(errors, list) or not errors:
        return

    first: object = cast(list[object], errors)[0]
    reason: object = (
        cast(dict[str, object], first).get("reason")
        if isinstance(first, dict)
        else None
    )
    code: str = reason if isinstance(reason, str) else "unknown"
    raise BusyTimeSourceError(
        f"Google free/busy cannot read the calendar ({code}).",
        CalendarSyncProblem.NOT_FOUND
        if code == "notFound"
        else CalendarSyncProblem.PROVIDER_ERROR,
    )


def read_period(item: object) -> BusyPeriod | None:
    """One {"start", "end"} pair of RFC 3339 instants; None when unusable."""

    if not isinstance(item, dict):
        return None

    fields: dict[str, object] = cast(dict[str, object], item)
    start: int | None = parse_instant(fields.get("start"))
    end: int | None = parse_instant(fields.get("end"))
    if start is None or end is None or end <= start or start < 0:
        return None

    return BusyPeriod(
        starts_at=BusyStartsAtUnixSeconds(start), ends_at=BusyEndsAtUnixSeconds(end)
    )


def parse_instant(value: object) -> int | None:
    if not isinstance(value, str):
        return None

    try:
        moment: datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return int(moment.timestamp()) if moment.tzinfo is not None else None


def read_calendar_entries(response: httpx.Response) -> list[GoogleCalendarEntry]:
    """The account's calendars, primary first, then by name."""

    ensure_readable(response, "Google calendar list")
    items: object = read_json_object(response, "Google calendar list").get("items")
    if not isinstance(items, list):
        return []

    entries: list[GoogleCalendarEntry] = [
        entry
        for item in cast(list[object], items)
        if (entry := read_calendar_entry(item)) is not None
    ]
    return sorted(entries, key=lambda entry: (not entry.is_primary, str(entry.name)))


def read_calendar_entry(item: object) -> GoogleCalendarEntry | None:
    if not isinstance(item, dict):
        return None

    fields: dict[str, object] = cast(dict[str, object], item)
    calendar_id: object = fields.get("id")
    if not isinstance(calendar_id, str) or calendar_id.strip() == "":
        return None

    name: object = fields.get("summaryOverride") or fields.get("summary")
    role: object = fields.get("accessRole")
    return GoogleCalendarEntry(
        calendar_id=ExternalCalendarId(calendar_id),
        name=CalendarDisplayName(
            (name if isinstance(name, str) and name.strip() else calendar_id).strip()[
                :MAX_CALENDAR_NAME_LENGTH
            ]
        ),
        access_role=GoogleCalendarAccessRole(
            role if isinstance(role, str) else "freeBusyReader"
        ),
        is_primary=fields.get("primary") is True,
    )
