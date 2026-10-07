"""
Google Calendar API v3 as the platform uses it: the documented answers
(events.list, an inserted event, freeBusy, calendarList) match Google's
discovery document and are read as expected; the event and free/busy
bodies the platform sends match it with every object closed; Google's
documented errors become the reasons the cabinet explains.
"""

from typing import Any

import pytest

from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import BusyWindow
from app.schemas.dto.operations.calendar_connection import CalendarEventDraft
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import CalendarRedirectUrl
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarEventDescription,
    CalendarEventId,
    CalendarEventTitle,
    ExternalCalendarId,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "google_calendar_api.json"
TOKEN = CalendarAccessToken("test-access-token-0000")
CALENDAR = ExternalCalendarId("studio@example.com")
TIMEOUT = BusyTimeFetchSeconds(5.0)
# 2026-10-01 00:00 UTC to 2026-10-08 00:00 UTC.
WINDOW = BusyWindow(
    starts_at=BusyStartsAtUnixSeconds(1_790_812_800),
    ends_at=BusyEndsAtUnixSeconds(1_791_417_600),
)
EVENT = CalendarEventDraft(
    title=CalendarEventTitle("Table for 4: Nino"),
    description=CalendarEventDescription("Booked by the AI assistant on the phone."),
    starts_at=BookingStartsAtUnixSeconds(1_791_039_600),
    ends_at=BookingEndsAtUnixSeconds(1_791_043_200),
    timezone=TimezoneName("Asia/Tbilisi"),
)


def fixture(name: str) -> Any:
    return load_json_fixture("google", name)


def client(transport: RecordingTransport) -> GoogleCalendarClient:
    return GoogleCalendarClient(
        client_id=PlatformIdentifier("client-id-0000.apps.googleusercontent.com"),
        client_secret=PlatformSecret("test-client-secret-0000"),
        redirect_url=CalendarRedirectUrl(
            "https://api.example.com/v1/integrations/google/callback"
        ),
        transport=transport.build(),
    )


@pytest.mark.parametrize(
    ("name", "root"),
    [
        ("events_list.json", "Events"),
        ("event_inserted.json", "Event"),
        ("free_busy_response.json", "FreeBusyResponse"),
        ("free_busy_not_found.json", "FreeBusyResponse"),
        ("calendar_list.json", "CalendarList"),
    ],
)
def test_documented_answers_match_the_discovery_document(name: str, root: str) -> None:
    assert_inbound(fixture(name), SPEC, root)


def test_event_requests_match_the_discovery_document() -> None:
    transport = RecordingTransport()
    transport.respond("GET", r"/events$", fixture("events_list.json"))
    transport.respond("POST", r"/events$", fixture("event_inserted.json"))
    transport.respond("PATCH", r"/events/[^/]+$", fixture("event_inserted.json"))
    google = client(transport)

    name = google.get_calendar_name(TOKEN, CALENDAR)
    event_id = google.insert_event(TOKEN, CALENDAR, EVENT)
    google.patch_event(TOKEN, CALENDAR, CalendarEventId(str(event_id)), EVENT)

    assert name == "Funicular VR: bookings"
    assert event_id == "7cbh8rpc10lrc0ckih9tafss99"
    _, inserted, patched = transport.requests
    assert_outbound(inserted.json(), SPEC, "Event")
    assert_outbound(patched.json(), SPEC, "Event")


def test_free_busy_request_matches_and_its_answer_is_read() -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/freeBusy$", fixture("free_busy_response.json"))

    periods = client(transport).query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    [request] = transport.requests
    assert_outbound(request.json(), SPEC, "FreeBusyRequest")
    assert [(int(period.starts_at), int(period.ends_at)) for period in periods] == [
        (1_791_039_600, 1_791_045_000),
        # 12:00 in Tbilisi (+04:00) is 08:00 UTC.
        (1_791_100_800, 1_791_104_400),
    ]


def test_a_calendar_google_cannot_find_is_not_found() -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/freeBusy$", fixture("free_busy_not_found.json"))

    with pytest.raises(BusyTimeSourceError) as raised:
        client(transport).query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    assert raised.value.problem is CalendarSyncProblem.NOT_FOUND


def test_calendar_list_is_read_primary_first() -> None:
    transport = RecordingTransport()
    transport.respond("GET", r"/calendarList$", fixture("calendar_list.json"))

    entries = client(transport).list_calendars(TOKEN, TIMEOUT)

    assert [
        (str(entry.calendar_id), str(entry.name), entry.is_primary) for entry in entries
    ] == [
        ("studio@example.com", "studio@example.com", True),
        ("c_0a1b2c3d4e5f@group.calendar.google.com", "Room 2 (VR)", False),
    ]


def test_token_grant_is_read() -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/token$", fixture("token_grant.json"))

    grant = client(transport).exchange_code(CalendarAuthorizationCode("4/0code-0000"))

    assert str(grant.access_token) == "test-access-token-0000"
    assert grant.refresh_token == "test-refresh-token-0000"
    assert int(grant.expires_in) == 3599


@pytest.mark.parametrize(
    "case", fixture("google_errors.json")["cases"], ids=lambda case: str(case["status"])
)
def test_documented_errors_become_the_reasons_owners_read(case: dict[str, Any]) -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/freeBusy$", case["body"], case["status"])

    with pytest.raises(BusyTimeSourceError) as raised:
        client(transport).query_free_busy(TOKEN, CALENDAR, WINDOW, TIMEOUT)

    assert raised.value.problem.value == case["problem"]
