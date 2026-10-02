"""The dashboard timeline agrees with `is_open_at`, second by second."""

import bisect
import random
from datetime import date, timedelta

import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.insights.dashboard_timeline import build_timeline, timeline_period
from app.utilities.scheduling.opening_hours import business_day_ranges, is_open_at
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    to_local_moment,
)
from tests.operations.builders import every_day, interval

WEEKDAY_HOURS = [
    interval(weekday, "09:00", "18:00")
    for weekday in (Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY)
]
OVERNIGHT_HOURS = every_day("18:00", "02:00")


@pytest.mark.parametrize(
    ("zone_name", "hours", "date_from", "date_to"),
    [
        ("Asia/Tbilisi", WEEKDAY_HOURS, date(2026, 10, 1), date(2026, 10, 14)),
        # Clocks go back one hour on 2026-10-25 in Berlin.
        ("Europe/Berlin", OVERNIGHT_HOURS, date(2026, 10, 20), date(2026, 10, 30)),
        # And forward on 2026-03-08 in New York.
        ("America/New_York", OVERNIGHT_HOURS, date(2026, 3, 5), date(2026, 3, 11)),
        (
            "Asia/Kolkata",
            every_day("00:00", "00:00"),
            date(2026, 6, 1),
            date(2026, 6, 3),
        ),
    ],
)
def test_stretches_say_open_exactly_when_the_business_is_open(
    zone_name: str, hours: list[OpeningInterval], date_from: date, date_to: date
) -> None:
    zone = load_time_zone(zone_name)
    holiday = ScheduleExceptionDocument(
        business_id=BusinessId(), date=LocalDate(str(date_from)), is_closed_all_day=True
    )
    ranges = business_day_ranges(hours, [holiday])
    stretches = build_timeline(date_from, date_to, zone, ranges)
    starts = [stretch.start for stretch in stretches]
    period_end = local_day_start_microseconds(date_to + timedelta(days=1), zone)
    chooser = random.Random(7)

    assert starts == sorted(set(starts))
    assert timeline_period(stretches, period_end).segment_starts[0] == starts[0]
    for _ in range(3_000):
        moment = chooser.randrange(starts[0], period_end)
        stretch = stretches[bisect.bisect_right(starts, moment) - 1]
        seconds = moment // 1_000_000
        local_day = (to_local_moment(seconds, zone).date() - date_from).days
        assert stretch.is_open == is_open_at(seconds, zone, ranges), moment
        assert stretch.day == local_day, moment


def test_without_hours_every_day_is_one_open_stretch() -> None:
    zone = load_time_zone("Asia/Tbilisi")
    stretches = build_timeline(date(2026, 10, 1), date(2026, 10, 3), zone, None)

    assert [(stretch.day, stretch.is_open) for stretch in stretches] == [
        (0, True),
        (1, True),
        (2, True),
    ]
