"""
Cal.com API v2 as the booking-system connector uses it: the documented
answers (an event type, a page of bookings, a created booking) match
Cal.com's specification and are read; the booking and cancellation the
platform sends match it with every object closed, for a language Cal.com
has and for one it has not; documented errors become the reasons the
cabinet explains.
"""

from typing import Any

import pytest

from app.adapters.booking_systems.cal_com_booking_system_adapter import (
    CalComBookingSystemAdapter,
)
from app.clients.cal_com.cal_com_client import CalComClient
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemBookingDraft,
    BookingSystemCredentials,
    BookingSystemRead,
    BusyWindow,
)
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
)
from app.schemas.typings.calendar_sync.strings import (
    BookingSystemApiKey,
    BookingSystemBookingId,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "cal_com_api_v2.json"
TIMEOUT = BusyTimeFetchSeconds(5.0)
CREDENTIALS = BookingSystemCredentials(
    api_key=BookingSystemApiKey("cal_test_key_0000"),
    external_resource_id=BookingSystemResourceId("1203845"),
)
# 2026-10-03 00:00 UTC to 2026-10-04 00:00 UTC.
WINDOW = BusyWindow(
    starts_at=BusyStartsAtUnixSeconds(1_790_985_600),
    ends_at=BusyEndsAtUnixSeconds(1_791_072_000),
)


def fixture(name: str) -> Any:
    return load_json_fixture("cal_com", name)


def connector(transport: RecordingTransport) -> CalComBookingSystemAdapter:
    return CalComBookingSystemAdapter(CalComClient(transport=transport.build()))


@pytest.mark.parametrize(
    ("name", "root"),
    [
        ("event_type.json", "response:event-types.get"),
        ("bookings_page.json", "response:bookings.list"),
        ("booking_created.json", "response:bookings.create"),
    ],
)
def test_documented_answers_match_the_specification(name: str, root: str) -> None:
    assert_inbound(fixture(name), SPEC, root)


def test_event_type_and_busy_bookings_are_read() -> None:
    transport = RecordingTransport()
    transport.respond("GET", r"/event-types/1203845$", fixture("event_type.json"))
    transport.respond("GET", r"/bookings$", fixture("bookings_page.json"))
    cal_com = connector(transport)

    resource = cal_com.describe(CREDENTIALS, TIMEOUT)
    busy = cal_com.list_busy(
        BookingSystemRead(credentials=CREDENTIALS, window=WINDOW, timeout=TIMEOUT)
    )

    assert str(resource.title) == "Haircut"
    # Accepted 07:00-07:30 and pending 07:15-08:00 merge; cancelled is free.
    assert [(int(period.starts_at), int(period.ends_at)) for period in busy] == [
        (1_791_010_800, 1_791_014_400)
    ]


@pytest.mark.parametrize(("language", "sent"), [("ru-GE", "ru"), ("ka-GE", None)])
def test_booking_and_cancellation_match_the_specification(
    language: str, sent: str | None
) -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/bookings$", fixture("booking_created.json"), 201)
    transport.respond("POST", r"/cancel$", {"status": "success", "data": {}})
    cal_com = connector(transport)
    draft = BookingSystemBookingDraft(
        starts_at=BusyStartsAtUnixSeconds(1_791_198_000),
        ends_at=BusyEndsAtUnixSeconds(1_791_199_800),
        guest_name=ContactName("Nino"),
        time_zone=TimezoneName("Asia/Tbilisi"),
        language=LanguageTag(language),
    )

    created = cal_com.create_booking(CREDENTIALS, draft, TIMEOUT)
    cal_com.cancel_booking(CREDENTIALS, created.booking_id, TIMEOUT)

    booking, cancellation = transport.requests
    assert_outbound(booking.json(), SPEC, "request:bookings.create")
    assert_outbound(cancellation.json(), SPEC, "request:bookings.cancel")
    assert booking.json()["attendee"].get("language") == sent
    assert created.booking_id == "uid-created-0004"


@pytest.mark.parametrize(
    "case",
    fixture("cal_com_errors.json")["cases"],
    ids=lambda case: str(case["status"]),
)
def test_documented_errors_become_the_reasons_owners_read(case: dict[str, Any]) -> None:
    transport = RecordingTransport()
    transport.respond("GET", r"/event-types/", case["body"], case["status"])

    with pytest.raises(BusyTimeSourceError) as raised:
        connector(transport).describe(CREDENTIALS, TIMEOUT)

    assert raised.value.problem.value == case["problem"]
    assert "cal_test_key_0000" not in str(raised.value)


def test_a_booking_gone_at_cal_com_is_cancelled_already() -> None:
    gone: dict[str, Any] = fixture("cal_com_errors.json")["cases"][2]
    transport = RecordingTransport()
    transport.respond("POST", r"/cancel$", gone["body"], gone["status"])

    connector(transport).cancel_booking(
        CREDENTIALS, BookingSystemBookingId("uid-gone-0000"), TIMEOUT
    )

    assert len(transport.requests) == 1
