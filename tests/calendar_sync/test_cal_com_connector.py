"""
The Cal.com connector against a fake Cal.com API v2: busy times across pages
(accepted and pending only, clipped and merged), the event type's title,
the bodies of booking writes, and what a refusal, a missing booking or a
timeout becomes.
"""

import json

import httpx
import pytest

from app.adapters.booking_systems.cal_com_booking_system_adapter import (
    CalComBookingSystemAdapter,
)
from app.clients.cal_com.cal_com_client import CalComClient
from app.registries.booking_systems.booking_system_connector_registry import (
    BookingSystemConnectorRegistry,
)
from app.schemas.constants.calendar_sync import BookingSystemKind, CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemBookingDraft,
    BookingSystemCredentials,
    BookingSystemRead,
    BusyWindow,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
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
from tests.calendar_sync.fake_cal_com import GOOD_KEY, FakeCalCom

TIMEOUT: BusyTimeFetchSeconds = BusyTimeFetchSeconds(2.0)
CREDENTIALS: BookingSystemCredentials = BookingSystemCredentials(
    api_key=BookingSystemApiKey(GOOD_KEY),
    external_resource_id=BookingSystemResourceId("1203845"),
)
# 2026-10-06 00:00 to 2026-10-07 00:00 UTC.
WINDOW: BusyWindow = BusyWindow(
    starts_at=BusyStartsAtUnixSeconds(1_791_244_800),
    ends_at=BusyEndsAtUnixSeconds(1_791_331_200),
)


def busy_of(fake: FakeCalCom) -> list[tuple[int, int]]:
    read = BookingSystemRead(credentials=CREDENTIALS, window=WINDOW, timeout=TIMEOUT)
    return [
        (int(period.starts_at), int(period.ends_at))
        for period in fake.adapter().list_busy(read)
    ]


def test_accepted_and_pending_bookings_are_busy_clipped_and_merged() -> None:
    fake = FakeCalCom()
    fake.book("2026-10-05T23:00:00.000Z", "2026-10-06T01:00:00.000Z")
    fake.book("2026-10-06T10:00:00.000Z", "2026-10-06T11:00:00.000Z", "pending")
    fake.book("2026-10-06T10:30:00.000Z", "2026-10-06T12:00:00.000Z")
    fake.book("2026-10-06T14:00:00.000Z", "2026-10-06T15:00:00.000Z", "cancelled")
    fake.book("2026-10-06T16:00:00.000Z", "2026-10-06T17:00:00.000Z", "rejected")

    assert busy_of(fake) == [
        (1_791_244_800, 1_791_248_400),
        (1_791_280_800, 1_791_288_000),
    ]
    request = fake.requests[0]
    assert request.headers["cal-api-version"] == "2024-08-13"
    assert request.url.params["eventTypeId"] == "1203845"
    assert request.url.params["afterStart"] == "2026-10-06T00:00:00Z"


def test_every_page_of_bookings_is_read() -> None:
    fake = FakeCalCom()
    for minute in range(0, 250):
        start = 1_791_244_800 + minute * 60
        fake.bookings.append(
            {
                "uid": f"u{minute}",
                "start": f"{start}",
                "end": "",
                "status": "accepted",
            }
        )
    fake.book("2026-10-06T20:00:00.000Z", "2026-10-06T21:00:00.000Z")

    assert busy_of(fake) == [(1_791_316_800, 1_791_320_400)]
    assert [request.url.params["skip"] for request in fake.requests] == [
        "0",
        "100",
        "200",
    ]


def test_the_event_type_is_described_with_its_title() -> None:
    described = FakeCalCom().adapter().describe(CREDENTIALS, TIMEOUT)

    assert str(described.title) == "Haircut"
    assert described.external_resource_id == CREDENTIALS.external_resource_id


def test_a_refused_key_and_an_unknown_event_type() -> None:
    adapter = FakeCalCom().adapter()
    wrong_key = CREDENTIALS.model_copy(
        update={"api_key": BookingSystemApiKey("cal_wrong_0000")}
    )
    unknown = CREDENTIALS.model_copy(
        update={"external_resource_id": BookingSystemResourceId("404")}
    )

    with pytest.raises(BusyTimeSourceError) as refused:
        adapter.describe(wrong_key, TIMEOUT)
    with pytest.raises(BusyTimeSourceError) as missing:
        adapter.describe(unknown, TIMEOUT)

    assert refused.value.problem is CalendarSyncProblem.ACCESS_DENIED
    assert missing.value.problem is CalendarSyncProblem.NOT_FOUND
    assert GOOD_KEY not in str(refused.value)


def test_a_slow_cal_com_times_out_and_an_unreachable_one_says_so() -> None:
    slow = FakeCalCom(is_slow=True)

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    unreachable = CalComBookingSystemAdapter(
        CalComClient(transport=httpx.MockTransport(refuse))
    )

    with pytest.raises(BusyTimeSourceError) as timed_out:
        slow.adapter().describe(CREDENTIALS, TIMEOUT)
    with pytest.raises(BusyTimeSourceError) as cut:
        unreachable.describe(CREDENTIALS, TIMEOUT)

    assert timed_out.value.problem is CalendarSyncProblem.TIMEOUT
    assert cut.value.problem is CalendarSyncProblem.UNREACHABLE


def test_a_booking_is_written_with_the_guest_name_only() -> None:
    fake = FakeCalCom()
    draft = BookingSystemBookingDraft(
        starts_at=BusyStartsAtUnixSeconds(1_791_280_800),
        ends_at=BusyEndsAtUnixSeconds(1_791_284_400),
        guest_name=ContactName("Nino"),
        time_zone=TimezoneName("Asia/Tbilisi"),
        language=LanguageTag("ka-GE"),
    )

    created = fake.adapter().create_booking(CREDENTIALS, draft, TIMEOUT)

    assert str(created.booking_id) == "created-1"
    assert fake.created == [
        {
            "start": "2026-10-06T10:00:00Z",
            "eventTypeId": 1203845,
            "lengthInMinutes": 60,
            "attendee": {"name": "Nino", "timeZone": "Asia/Tbilisi", "language": "ka"},
            "metadata": {"source": "assistant-workshop"},
        }
    ]


def test_cancelling_a_booking_that_is_gone_already_is_fine() -> None:
    fake = FakeCalCom()
    adapter = fake.adapter()

    adapter.cancel_booking(CREDENTIALS, BookingSystemBookingId("uid-1"), TIMEOUT)
    adapter.cancel_booking(CREDENTIALS, BookingSystemBookingId("gone-2"), TIMEOUT)

    bodies = [json.loads(request.content) for request in fake.requests]
    assert [request.url.path for request in fake.requests] == [
        "/v2/bookings/uid-1/cancel",
        "/v2/bookings/gone-2/cancel",
    ]
    assert bodies[0] == {"cancellationReason": "Cancelled in Assistant Workshop"}


def test_the_registry_finds_connectors_by_kind() -> None:
    registry = BookingSystemConnectorRegistry([FakeCalCom().adapter()])
    empty = BookingSystemConnectorRegistry([])

    assert registry.kinds() == [BookingSystemKind.CAL_COM]
    assert registry.connector_for(BookingSystemKind.CAL_COM).kind is (
        BookingSystemKind.CAL_COM
    )
    with pytest.raises(ValidationFailedError):
        empty.connector_for(BookingSystemKind.CAL_COM)
