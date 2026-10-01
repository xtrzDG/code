from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.scheduling.nights import (
    StayTimes,
    find_time_in_text,
    read_stay_times,
    stay_bounds,
    stay_dates,
)
from app.utilities.scheduling.opening_hours import (
    MinuteRange,
    business_day_ranges,
    business_ranges_starting_on,
    find_next_opening,
    intersect_ranges,
    is_open_at,
    is_open_on_date,
    merge_ranges,
    ranges_around,
    resource_ranges_starting_on,
)
from app.utilities.scheduling.overlap import BusyRange, max_concurrent_overlap
from app.utilities.scheduling.slots import (
    fit_slot,
    generate_slots,
    nearest_minutes,
    slot_step_minutes,
)
from app.utilities.scheduling.zoned_time import (
    find_utc_seconds,
    lenient_utc_seconds,
    load_time_zone,
    parse_local_date,
    parse_time_of_day,
    require_utc_seconds,
    to_local_moment,
    to_time_of_day,
)
from tests.operations.builders import OperationsWorld, every_day, interval, minute

NEW_YORK: ZoneInfo = ZoneInfo("America/New_York")
TBILISI: ZoneInfo = ZoneInfo("Asia/Tbilisi")
KOLKATA: ZoneInfo = ZoneInfo("Asia/Kolkata")
AUCKLAND: ZoneInfo = ZoneInfo("Pacific/Auckland")
ROME: ZoneInfo = ZoneInfo("Europe/Rome")


def utc_seconds(text: str) -> int:
    return int(datetime.fromisoformat(text).astimezone(UTC).timestamp())


def exception(
    day: str,
    resource_id: ResourceId | None = None,
    special: list[tuple[str, str]] | None = None,
    is_closed_all_day: bool | None = None,
) -> ScheduleExceptionDocument:
    return ScheduleExceptionDocument(
        business_id=BusinessId(),
        resource_id=resource_id,
        date=LocalDate(day),
        is_closed_all_day=(
            not special if is_closed_all_day is None else is_closed_all_day
        ),
        special_hours=[
            interval(Weekday.MONDAY, opens, closes) for opens, closes in special or []
        ],
    )


class TestZonedTime:
    def test_unknown_zone_and_impossible_date_are_validation_errors(self) -> None:
        with pytest.raises(ValidationFailedError):
            load_time_zone(TimezoneName("Mars/Olympus_Mons"))

        with pytest.raises(ValidationFailedError):
            parse_local_date(LocalDate("2026-02-30"))

    def test_time_of_day_round_trip_wraps_midnight(self) -> None:
        assert parse_time_of_day(LocalTimeOfDay("19:30")) == 19 * 60 + 30
        assert to_time_of_day(25 * 60 + 5) == "01:05"
        assert to_time_of_day(-30) == "23:30"

    def test_new_york_spring_forward_gap_is_rejected(self) -> None:
        gap_day = date(2026, 3, 8)
        assert find_utc_seconds(gap_day, minute("02:30"), NEW_YORK) is None
        with pytest.raises(ValidationFailedError, match="does not exist"):
            require_utc_seconds(gap_day, minute("02:30"), NEW_YORK)

        # The bound of an opening range in the gap maps past the jump.
        assert lenient_utc_seconds(gap_day, minute("02:30"), NEW_YORK) == (
            utc_seconds("2026-03-08T07:30:00+00:00")
        )

    def test_new_york_fall_back_fold_uses_first_occurrence(self) -> None:
        fold_day = date(2026, 11, 1)
        assert require_utc_seconds(fold_day, minute("01:30"), NEW_YORK) == (
            utc_seconds("2026-11-01T01:30:00-04:00")
        )

    def test_half_hour_and_southern_hemisphere_offsets(self) -> None:
        assert require_utc_seconds(date(2026, 10, 5), minute("19:00"), KOLKATA) == (
            utc_seconds("2026-10-05T13:30:00+00:00")
        )
        # New Zealand daylight time starts on 2026-09-27 (02:00 -> 03:00).
        assert find_utc_seconds(date(2026, 9, 27), minute("02:15"), AUCKLAND) is None
        assert require_utc_seconds(date(2026, 10, 5), minute("19:00"), AUCKLAND) == (
            utc_seconds("2026-10-05T19:00:00+13:00")
        )

    def test_local_moment_of_utc_seconds(self) -> None:
        moment = to_local_moment(utc_seconds("2026-10-05T08:00:00+00:00"), TBILISI)
        assert (moment.hour, moment.minute) == (12, 0)


class TestOpeningHours:
    def test_overnight_range_spills_into_the_next_day(self) -> None:
        bar_hours = [interval(Weekday.FRIDAY, "18:00", "02:00")]
        ranges = business_day_ranges(bar_hours, [])
        friday, saturday = date(2026, 10, 9), date(2026, 10, 10)

        assert ranges(friday) == [MinuteRange(18 * 60, 26 * 60)]
        assert ranges_around(saturday, ranges) == [MinuteRange(-6 * 60, 2 * 60)]
        assert is_open_on_date(saturday, ranges)
        assert is_open_at(utc_seconds("2026-10-10T01:30:00+04:00"), TBILISI, ranges)
        assert not is_open_at(utc_seconds("2026-10-10T02:30:00+04:00"), TBILISI, ranges)

    def test_split_and_touching_ranges_are_merged(self) -> None:
        assert merge_ranges(
            [MinuteRange(900, 1440), MinuteRange(600, 900), MinuteRange(1500, 1600)]
        ) == [MinuteRange(600, 1440), MinuteRange(1500, 1600)]
        assert intersect_ranges([MinuteRange(600, 1000)], [MinuteRange(800, 1200)]) == [
            MinuteRange(800, 1000)
        ]

    def test_business_holiday_and_special_hours(self) -> None:
        hours = every_day("12:00", "23:00")
        holiday = exception("2026-10-05")
        short_day = exception("2026-10-06", special=[("12:00", "16:00")])
        note_only = exception("2026-10-07", is_closed_all_day=False)
        exceptions = [holiday, short_day, note_only]

        assert business_ranges_starting_on(date(2026, 10, 5), hours, exceptions) == []
        assert business_ranges_starting_on(date(2026, 10, 6), hours, exceptions) == [
            MinuteRange(12 * 60, 16 * 60)
        ]
        assert business_ranges_starting_on(date(2026, 10, 7), hours, exceptions) == [
            MinuteRange(12 * 60, 23 * 60)
        ]

    def test_resource_level_exception_wins_over_business_level(self) -> None:
        resource_id = ResourceId()
        hours = every_day("10:00", "22:00")
        staff_schedule = [interval(Weekday.TUESDAY, "10:00", "14:00")]
        exceptions = [
            exception("2026-10-05"),
            exception("2026-10-05", resource_id, special=[("18:00", "23:00")]),
            exception("2026-10-06", special=[("12:00", "16:00")]),
        ]

        # Business closed, but the banquet hall opens for an event.
        assert resource_ranges_starting_on(
            date(2026, 10, 5), resource_id, [], hours, exceptions
        ) == [MinuteRange(18 * 60, 23 * 60)]
        # Business special hours are intersected with the staff schedule.
        assert resource_ranges_starting_on(
            date(2026, 10, 6), resource_id, staff_schedule, hours, exceptions
        ) == [MinuteRange(12 * 60, 14 * 60)]
        # Another resource follows the business holiday.
        assert (
            resource_ranges_starting_on(
                date(2026, 10, 5), ResourceId(), [], hours, exceptions
            )
            == []
        )

    def test_next_opening_skips_closed_days_in_jerusalem(self) -> None:
        jerusalem = ZoneInfo("Asia/Jerusalem")
        weekdays = [
            interval(weekday, "09:00", "18:00")
            for weekday in (
                Weekday.SUNDAY,
                Weekday.MONDAY,
                Weekday.TUESDAY,
                Weekday.WEDNESDAY,
                Weekday.THURSDAY,
            )
        ]
        ranges = business_day_ranges(weekdays, [])
        friday_evening = utc_seconds("2026-10-09T20:00:00+03:00")

        reopening = find_next_opening(friday_evening, jerusalem, ranges)

        assert reopening is not None
        assert (reopening.date(), reopening.hour) == (date(2026, 10, 11), 9)
        no_hours = business_day_ranges([], [])
        assert find_next_opening(friday_evening, jerusalem, no_hours) is None


class TestSlotsAndOverlap:
    def test_slots_step_by_half_an_hour_and_fit_the_range(self) -> None:
        day = date(2026, 10, 5)
        slots = generate_slots(day, TBILISI, [MinuteRange(12 * 60, 15 * 60)], 120)

        assert slot_step_minutes(120) == 30
        assert slot_step_minutes(15) == 15
        assert [to_time_of_day(slot.minute_of_day) for slot in slots] == [
            "12:00",
            "12:30",
            "13:00",
        ]
        assert slots[0].ends_at - slots[0].starts_at == 120 * 60

    def test_slots_skip_the_daylight_saving_gap(self) -> None:
        gap_day = date(2026, 3, 8)
        slots = generate_slots(gap_day, NEW_YORK, [MinuteRange(0, 6 * 60)], 60)
        starts = [to_time_of_day(slot.minute_of_day) for slot in slots]

        assert "02:00" not in starts and "02:30" not in starts
        assert starts[:4] == ["00:00", "00:30", "01:00", "01:30"]
        # 01:30-02:30 wall time lasts one real hour: 01:30 EST to 03:30 EDT.
        assert slots[3].ends_at - slots[3].starts_at == 3600

    def test_slots_from_the_previous_evening_start_after_midnight(self) -> None:
        slots = generate_slots(
            date(2026, 10, 10), TBILISI, [MinuteRange(-350, 120)], 60
        )
        assert [to_time_of_day(slot.minute_of_day) for slot in slots] == [
            "00:10",
            "00:40",
        ]

    def test_fit_slot_requires_the_whole_slot_inside_a_range(self) -> None:
        day = date(2026, 10, 5)
        ranges = [MinuteRange(12 * 60, 23 * 60)]
        assert fit_slot(day, minute("21:00"), ROME, ranges, 120) is not None
        assert fit_slot(day, minute("21:30"), ROME, ranges, 120) is None
        assert fit_slot(day, minute("11:00"), ROME, ranges, 60) is None

    def test_nearest_minutes_are_returned_in_time_order(self) -> None:
        minutes = [600, 630, 660, 690, 720, 750, 780]
        assert nearest_minutes(minutes, 700, 3) == [660, 690, 720]

    def test_peak_overlap_counts_identical_units(self) -> None:
        busy = [BusyRange(0, 100), BusyRange(50, 150), BusyRange(200, 300)]
        assert max_concurrent_overlap(busy, 0, 300) == 2
        assert max_concurrent_overlap(busy, 100, 200) == 1
        # Touching ranges do not overlap.
        assert max_concurrent_overlap(busy, 150, 200) == 0
        # Two units, stays on night 1 and night 3: a whole-range count would
        # wrongly refuse a third stay over nights 1-3.
        assert max_concurrent_overlap([BusyRange(0, 10), BusyRange(20, 30)], 0, 30) == 1


class TestNights:
    def test_stay_dates_and_bounds_use_check_in_and_out_times(self) -> None:
        check_in = date(2026, 10, 5)
        bounds = stay_bounds(check_in, 3, StayTimes(14 * 60, 11 * 60), TBILISI)

        assert stay_dates(check_in, 3) == [
            date(2026, 10, 5),
            date(2026, 10, 6),
            date(2026, 10, 7),
        ]
        assert bounds.starts_at == utc_seconds("2026-10-05T14:00:00+04:00")
        assert bounds.ends_at == utc_seconds("2026-10-08T11:00:00+04:00")

    def test_stay_times_come_from_profile_answers(self) -> None:
        world = OperationsWorld()
        business = world.add_business(country_code="AM", timezone="Asia/Yerevan")
        profile = world.add_profile(
            business,
            niche_answers={
                "check_in_time": "from 15.00",
                "check_out_time": "Check-out until 11:30, late on request",
            },
        )

        assert read_stay_times(profile) == StayTimes(15 * 60, 11 * 60 + 30)
        assert read_stay_times(None) == StayTimes(14 * 60, 12 * 60)
        assert find_time_in_text("no time here") is None
