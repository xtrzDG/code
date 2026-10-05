"""
Booking slots on the days clocks change, in five time zones (forward and
back, northern and southern, a half-hour shift, a change at midnight):
every slot lasts its real duration, starts at an existing wall time on its
own date, on the step grid, inside the opening range, once; and every
grid start that exists and fits is offered.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given
from hypothesis import strategies as st

from app.utilities.scheduling.opening_hours import MinuteRange
from app.utilities.scheduling.slots import generate_slots, slot_step_minutes
from app.utilities.scheduling.zoned_time import (
    MINUTES_PER_DAY,
    find_utc_seconds,
    lenient_utc_seconds,
)

ZONES: tuple[str, ...] = (
    "Europe/Berlin",  # northern, at 02:00 and 03:00
    "America/New_York",
    "Australia/Sydney",  # southern: back in April, forward in October
    "America/Santiago",  # changes at midnight: some days start at 01:00
    "Australia/Lord_Howe",  # a half-hour shift
)
YEAR: int = 2026


def transition_dates(zone: ZoneInfo, year: int) -> list[date]:
    """The local dates of `year` whose UTC offset changes during the day."""

    days: list[date] = []
    day = date(year, 1, 1)
    while day.year == year:
        start = datetime(day.year, day.month, day.day, tzinfo=zone)
        end = start + timedelta(days=1)
        if start.utcoffset() != end.utcoffset():
            days.append(day)
        day += timedelta(days=1)
    return days


TRANSITIONS: dict[str, list[date]] = {
    name: transition_dates(ZoneInfo(name), YEAR) for name in ZONES
}


@st.composite
def zoned_days(draw: st.DrawFn) -> tuple[ZoneInfo, date]:
    name = draw(st.sampled_from(ZONES))
    around = draw(st.sampled_from(TRANSITIONS[name]))
    return ZoneInfo(name), around + timedelta(days=draw(st.integers(-1, 1)))


@st.composite
def opening_ranges(draw: st.DrawFn) -> MinuteRange:
    start = draw(st.integers(min_value=0, max_value=MINUTES_PER_DAY - 15))
    end = draw(st.integers(min_value=start + 15, max_value=MINUTES_PER_DAY))
    return MinuteRange(start, end)


durations = st.sampled_from([15, 20, 30, 45, 60, 90, 120, 180])


def test_every_zone_changes_its_clocks_twice_a_year() -> None:
    assert {name: len(days) for name, days in TRANSITIONS.items()} == dict.fromkeys(
        ZONES, 2
    )


@given(zoned_days(), opening_ranges(), durations)
def test_slots_on_a_clock_change_day_are_real_and_complete(
    zoned_day: tuple[ZoneInfo, date], opening: MinuteRange, duration: int
) -> None:
    zone, local_date = zoned_day

    slots = generate_slots(local_date, zone, [opening], duration)

    step = slot_step_minutes(duration)
    opens_at = lenient_utc_seconds(local_date, opening.start, zone)
    closes_at = lenient_utc_seconds(local_date, opening.end, zone)
    for slot in slots:
        assert slot.ends_at - slot.starts_at == duration * 60
        assert opens_at <= slot.starts_at and slot.ends_at <= closes_at
        assert (slot.minute_of_day - opening.start) % step == 0
        local = datetime.fromtimestamp(slot.starts_at, UTC).astimezone(zone)
        assert local.date() == local_date
        assert local.hour * 60 + local.minute == slot.minute_of_day
    starts = [slot.starts_at for slot in slots]
    assert starts == sorted(set(starts))

    offered = {slot.minute_of_day for slot in slots}
    for minute in range(opening.start, min(opening.end, MINUTES_PER_DAY), step):
        start = find_utc_seconds(local_date, minute, zone)
        fits = (
            start is not None
            and opens_at <= start
            and start + duration * 60 <= closes_at
        )
        assert (minute in offered) == fits, (zone.key, local_date, minute)
