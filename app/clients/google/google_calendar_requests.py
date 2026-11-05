"""Addresses, headers and bodies of Google Calendar API requests."""

from datetime import UTC, datetime
from urllib.parse import quote

from app.schemas.dto.operations.calendar_connection import CalendarEventDraft
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarEventId,
    ExternalCalendarId,
)

GOOGLE_CALENDAR_API_BASE_URL: str = "https://www.googleapis.com/calendar/v3"


def events_url(calendar_id: ExternalCalendarId) -> str:
    return (
        f"{GOOGLE_CALENDAR_API_BASE_URL}/calendars/"
        f"{quote(str(calendar_id), safe='')}/events"
    )


def event_url(calendar_id: ExternalCalendarId, event_id: CalendarEventId) -> str:
    return f"{events_url(calendar_id)}/{quote(str(event_id), safe='')}"


def bearer(access_token: CalendarAccessToken) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def event_body(event: CalendarEventDraft) -> dict[str, object]:
    """Event resource with UTC instants and the business zone for display."""

    return {
        "summary": str(event.title),
        "description": str(event.description),
        "start": {
            "dateTime": format_rfc3339(int(event.starts_at)),
            "timeZone": str(event.timezone),
        },
        "end": {
            "dateTime": format_rfc3339(int(event.ends_at)),
            "timeZone": str(event.timezone),
        },
    }


def format_rfc3339(unix_seconds: int) -> str:
    return (
        datetime.fromtimestamp(unix_seconds, tz=UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
