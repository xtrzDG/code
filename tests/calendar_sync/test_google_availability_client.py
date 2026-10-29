"""
The Google client's availability side against scripted answers: free/busy
periods read (unusable ones skipped), the calendar list (primary first),
and every failure read into the reason the cabinet explains, never with
the access token in it.
"""

from collections.abc import Callable

import httpx
import pytest

from app.clients.google.google_calendar_client import (
    GOOGLE_CALENDAR_SCOPES,
    GoogleCalendarClient,
)
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import BusyWindow
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.strings import CalendarAccessToken, ExternalCalendarId
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)

TOKEN: CalendarAccessToken = CalendarAccessToken("access-test-0000")
CALENDAR: ExternalCalendarId = ExternalCalendarId("room-1@group.calendar.google.com")
TIMEOUT: BusyTimeFetchSeconds = BusyTimeFetchSeconds(2.0)
WINDOW: BusyWindow = BusyWindow(
    starts_at=BusyStartsAtUnixSeconds(1_791_244_800),
    ends_at=BusyEndsAtUnixSeconds(1_791_331_200),
)

type Answer = Callable[[httpx.Request], httpx.Response]


def client(answer: Answer) -> tuple[GoogleCalendarClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answer(request)

    return (
        GoogleCalendarClient(None, None, None, transport=httpx.MockTransport(handle)),
        seen,
    )


def free_busy(calendar_entry: object) -> Answer:
    return lambda _: httpx.Response(
        200, json={"calendars": {str(CALENDAR): calendar_entry}}
    )


def status(code: int, body: object | None = None) -> Answer:
    return lambda _: httpx.Response(code, json={} if body is None else body)


def problem_of(answer: Answer) -> CalendarSyncProblem:
    google, _ = client(answer)
    with pytest.raises(BusyTimeSourceError) as raised:
        google.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)
    assert str(TOKEN) not in str(raised.value)
    return raised.value.problem


def test_busy_periods_are_read_and_unusable_ones_skipped() -> None:
    google, seen = client(
        free_busy(
            {
                "busy": [
                    {"start": "2026-10-06T10:00:00Z", "end": "2026-10-06T11:00:00Z"},
                    {"start": "2026-10-06T14:00:00+04:00", "end": "bad"},
                    {"start": "2026-10-06T12:00:00", "end": "2026-10-06T13:00:00"},
                    {"start": "2026-10-06T15:00:00Z", "end": "2026-10-06T15:00:00Z"},
                    "nonsense",
                ]
            }
        )
    )

    periods = google.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    assert [(int(p.starts_at), int(p.ends_at)) for p in periods] == [
        (1_791_280_800, 1_791_284_400)
    ]
    assert seen[0].headers["Authorization"] == f"Bearer {TOKEN}"
    assert seen[0].url.path == "/calendar/v3/freeBusy"


def test_a_calendar_without_busy_times_is_free() -> None:
    google, _ = client(free_busy({}))

    assert google.query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT) == []


@pytest.mark.parametrize(
    ("answer", "problem"),
    [
        (status(401), CalendarSyncProblem.NEEDS_RECONNECT),
        (status(403), CalendarSyncProblem.NEEDS_RECONNECT),
        (status(404), CalendarSyncProblem.NOT_FOUND),
        (status(500), CalendarSyncProblem.PROVIDER_ERROR),
        (
            free_busy({"errors": [{"reason": "notFound"}]}),
            CalendarSyncProblem.NOT_FOUND,
        ),
        (
            free_busy({"errors": [{"reason": "internalError"}]}),
            CalendarSyncProblem.PROVIDER_ERROR,
        ),
        (status(200, {"calendars": {}}), CalendarSyncProblem.PROVIDER_ERROR),
    ],
)
def test_failures_become_the_reason_to_explain(
    answer: Answer, problem: CalendarSyncProblem
) -> None:
    assert problem_of(answer) is problem


def test_a_slow_or_unreachable_google_says_so() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert problem_of(slow) is CalendarSyncProblem.TIMEOUT
    assert problem_of(unreachable) is CalendarSyncProblem.UNREACHABLE


def test_the_calendar_list_puts_the_primary_calendar_first() -> None:
    google, seen = client(
        lambda _: httpx.Response(
            200,
            json={
                "items": [
                    {"id": "b@group", "summary": "Bar", "accessRole": "reader"},
                    {"id": "me@x.com", "primary": True, "accessRole": "owner"},
                    {"id": "a@group", "summaryOverride": "Arena", "summary": "x"},
                    {"id": " "},
                    "nonsense",
                ]
            },
        )
    )

    entries = google.list_calendars(TOKEN, TIMEOUT)

    assert [(str(e.calendar_id), str(e.name)) for e in entries] == [
        ("me@x.com", "me@x.com"),
        ("a@group", "Arena"),
        ("b@group", "Bar"),
    ]
    assert entries[0].is_primary is True
    assert str(entries[1].access_role) == "freeBusyReader"
    assert seen[0].url.params["minAccessRole"] == "freeBusyReader"


def test_the_calendar_list_needs_the_read_permission() -> None:
    google, _ = client(status(403))

    with pytest.raises(BusyTimeSourceError) as raised:
        google.list_calendars(TOKEN, TIMEOUT)

    assert raised.value.problem is CalendarSyncProblem.NEEDS_RECONNECT


def test_consent_asks_for_reading_calendars_too() -> None:
    assert GOOGLE_CALENDAR_SCOPES.split() == [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]
