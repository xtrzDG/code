"""
Reading imported iCal feeds: an Airbnb export's whole-day reservations,
timed events with and without a zone, repeating events, free and cancelled
events left out, merging, the window and the limit, and text that is no
calendar at all.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import BusyWindow
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.constrained_integers import ResourceCapacity
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.utilities.calendar_sync.busy_windows import whole_day_bounds
from app.utilities.calendar_sync.ical_busy_times import read_feed_busy_periods
from app.utilities.scheduling.nights import StayTimes
from tests.calendar_sync.calendar_shop import calendar_ics

TBILISI: ZoneInfo = ZoneInfo("Asia/Tbilisi")
STAY_TIMES: StayTimes = StayTimes(check_in_minute=14 * 60, check_out_minute=12 * 60)
# What Airbnb exports: reservations and blocked nights as whole days.
AIRBNB_FEED: str = calendar_ics(
    "DTEND;VALUE=DATE:20261013\r\nDTSTART;VALUE=DATE:20261010\r\n"
    "UID:1418fb94e984-reservation@airbnb.com\r\nSUMMARY:Reserved",
    "DTEND;VALUE=DATE:20261016\r\nDTSTART;VALUE=DATE:20261015\r\n"
    "UID:7f3c-blocked@airbnb.com\r\nSUMMARY:Airbnb (Not available)",
)


def utc(*parts: int) -> int:
    return int(datetime(*parts, tzinfo=UTC).timestamp())


def window(start: int = utc(2026, 10, 1), end: int = utc(2027, 1, 1)) -> BusyWindow:
    return BusyWindow(
        starts_at=BusyStartsAtUnixSeconds(start), ends_at=BusyEndsAtUnixSeconds(end)
    )


def resource(unit: BookingUnit) -> ResourceDocument:
    return ResourceDocument(
        business_id=BusinessId("business_00000000-0000-4000-8000-000000000001"),
        kind=ResourceKind.ROOM if unit is BookingUnit.NIGHT else ResourceKind.TABLE,
        name=ResourceName("Sea view"),
        capacity=ResourceCapacity(2),
        booking_unit=unit,
    )


def read(text: str, unit: BookingUnit = BookingUnit.TIME_SLOT, limit: int = 100):
    bounds = whole_day_bounds(resource(unit), TBILISI, STAY_TIMES)
    return [
        (int(period.starts_at), int(period.ends_at))
        for period in read_feed_busy_periods(
            text.encode("utf-8"), window(), TBILISI, bounds, limit
        )
    ]


def test_whole_day_reservations_of_a_room_run_from_check_in_to_check_out() -> None:
    # Check-in 14:00 and check-out 12:00 in Tbilisi (UTC+4).
    assert read(AIRBNB_FEED, BookingUnit.NIGHT) == [
        (utc(2026, 10, 10, 10), utc(2026, 10, 13, 8)),
        (utc(2026, 10, 15, 10), utc(2026, 10, 16, 8)),
    ]


def test_whole_days_of_other_resources_are_the_local_days() -> None:
    assert read(AIRBNB_FEED) == [
        (utc(2026, 10, 9, 20), utc(2026, 10, 12, 20)),
        (utc(2026, 10, 14, 20), utc(2026, 10, 15, 20)),
    ]


def test_zoned_utc_and_floating_times() -> None:
    feed = calendar_ics(
        "UID:a\r\nDTSTART;TZID=Europe/Berlin:20261020T100000\r\n"
        "DTEND;TZID=Europe/Berlin:20261020T110000",
        "UID:b\r\nDTSTART:20261021T090000Z\r\nDURATION:PT90M",
        "UID:c\r\nDTSTART:20261022T150000\r\nDTEND:20261022T160000",
    )

    assert read(feed) == [
        (utc(2026, 10, 20, 8), utc(2026, 10, 20, 9)),
        (utc(2026, 10, 21, 9), utc(2026, 10, 21, 10, 30)),
        # Floating: the business's local time.
        (utc(2026, 10, 22, 11), utc(2026, 10, 22, 12)),
    ]


def test_repeating_events_are_expanded_and_exceptions_left_out() -> None:
    feed = calendar_ics(
        "UID:weekly\r\nDTSTART:20261005T060000Z\r\nDTEND:20261005T070000Z\r\n"
        "RRULE:FREQ=WEEKLY;COUNT=3\r\nEXDATE:20261012T060000Z"
    )

    assert read(feed) == [
        (utc(2026, 10, 5, 6), utc(2026, 10, 5, 7)),
        (utc(2026, 10, 19, 6), utc(2026, 10, 19, 7)),
    ]


def test_free_and_cancelled_events_block_nothing_and_overlaps_merge() -> None:
    feed = calendar_ics(
        "UID:free\r\nDTSTART:20261020T060000Z\r\nDTEND:20261020T070000Z\r\n"
        "TRANSP:TRANSPARENT",
        "UID:off\r\nDTSTART:20261020T080000Z\r\nDTEND:20261020T090000Z\r\n"
        "STATUS:CANCELLED",
        "UID:x\r\nDTSTART:20261021T060000Z\r\nDTEND:20261021T080000Z",
        "UID:y\r\nDTSTART:20261021T070000Z\r\nDTEND:20261021T090000Z",
        "UID:zero\r\nDTSTART:20261022T060000Z\r\nDTEND:20261022T060000Z",
    )

    assert read(feed) == [(utc(2026, 10, 21, 6), utc(2026, 10, 21, 9))]


def test_events_outside_the_window_are_left_out_and_edges_clipped() -> None:
    feed = calendar_ics(
        "UID:old\r\nDTSTART:20260901T060000Z\r\nDTEND:20260901T070000Z",
        "UID:edge\r\nDTSTART:20260930T220000Z\r\nDTEND:20261001T020000Z",
    )

    assert read(feed) == [(utc(2026, 10, 1), utc(2026, 10, 1, 2))]


def test_at_most_the_limit_is_kept() -> None:
    feed = calendar_ics(
        *(
            f"UID:d{day}\r\nDTSTART:202610{day:02d}T060000Z\r\n"
            f"DTEND:202610{day:02d}T070000Z"
            for day in range(1, 11)
        )
    )

    assert len(read(feed, limit=3)) == 3


@pytest.mark.parametrize(
    "body",
    ["<html><body>Sign in</body></html>", "", "BEGIN:VEVENT\r\nEND:VEVENT\r\n"],
)
def test_text_that_is_no_calendar_is_reported(body: str) -> None:
    with pytest.raises(BusyTimeSourceError) as raised:
        read(body)

    assert raised.value.problem is CalendarSyncProblem.NOT_A_CALENDAR


def test_whole_day_bounds_of_a_room_across_a_clock_change() -> None:
    bounds = whole_day_bounds(
        resource(BookingUnit.NIGHT), ZoneInfo("Europe/Berlin"), STAY_TIMES
    )

    # Summer time ends on 25 October 2026 in Berlin.
    assert bounds(date(2026, 10, 24), date(2026, 10, 26)) == (
        utc(2026, 10, 24, 12),
        utc(2026, 10, 26, 11),
    )
