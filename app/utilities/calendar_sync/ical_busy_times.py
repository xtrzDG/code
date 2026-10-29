"""
The busy times of an imported iCalendar feed (RFC 5545): Airbnb's and
Booking.com's reservations and closed nights, a public calendar's events.
Repeating events are expanded within the window; free (TRANSPARENT) and
cancelled events are left out; overlapping times are merged.

Times with a zone are exact; floating times (no zone) are the business's
local time; whole-day events become the times `day_bounds` gives their
dates (a night resource: check-in to check-out, so a guest leaving on the
day another arrives never collides; otherwise the whole local days).
"""

import datetime
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.dto.calendar_sync.busy_reads import BusyPeriod, BusyWindow
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.utilities.calendar_sync.busy_periods import (
    clip_to_window,
    merge_busy_periods,
    new_period,
)
from app.utilities.calendar_sync.busy_windows import DayBounds

NOT_A_CALENDAR_MESSAGE: str = "The address does not serve an iCalendar feed."
FREE_TRANSPARENCY: str = "TRANSPARENT"
CANCELLED_STATUS: str = "CANCELLED"
ONE_DAY: datetime.timedelta = datetime.timedelta(days=1)


def read_feed_busy_periods(
    body: bytes,
    window: BusyWindow,
    zone: ZoneInfo,
    day_bounds: DayBounds,
    limit: int,
) -> list[BusyPeriod]:
    """
    The feed's busy times within the window, merged, at most `limit`.

    Raises:
        BusyTimeSourceError: NOT_A_CALENDAR when the body is no calendar.
    """

    calendar: icalendar.Component = parse_calendar(body)
    start = datetime.datetime.fromtimestamp(int(window.starts_at), tz=datetime.UTC)
    stop = datetime.datetime.fromtimestamp(int(window.ends_at), tz=datetime.UTC)
    try:
        occurrences: list[icalendar.Component] = recurring_ical_events.of(
            calendar, skip_bad_series=True
        ).between(start, stop)
    except (ValueError, TypeError, OverflowError) as error:
        raise BusyTimeSourceError(
            NOT_A_CALENDAR_MESSAGE, CalendarSyncProblem.NOT_A_CALENDAR
        ) from error

    periods: list[BusyPeriod] = []
    for event in occurrences:
        if is_free(event):
            continue

        period: BusyPeriod | None = event_period(event, zone, day_bounds)
        clipped: BusyPeriod | None = (
            None if period is None else clip_to_window(period, window)
        )
        if clipped is not None:
            periods.append(clipped)

    return merge_busy_periods(periods)[:limit]


def parse_calendar(body: bytes) -> icalendar.Component:
    """
    The feed as one VCALENDAR. The body is passed as bytes on purpose: the
    library reads a str without line breaks as a path to a local file.
    """

    try:
        calendar: icalendar.Component = icalendar.Calendar.from_ical(body)
    except (ValueError, TypeError, IndexError, KeyError) as error:
        raise BusyTimeSourceError(
            NOT_A_CALENDAR_MESSAGE, CalendarSyncProblem.NOT_A_CALENDAR
        ) from error

    if str(calendar.name).upper() != "VCALENDAR":
        raise BusyTimeSourceError(
            NOT_A_CALENDAR_MESSAGE, CalendarSyncProblem.NOT_A_CALENDAR
        )

    return calendar


def is_free(event: icalendar.Component) -> bool:
    """A TRANSPARENT ("show as free") or cancelled event blocks nothing."""

    transparency: object = event.get("TRANSP")
    status: object = event.get("STATUS")
    return (
        str(transparency or "").upper() == FREE_TRANSPARENCY
        or str(status or "").upper() == CANCELLED_STATUS
    )


def event_period(
    event: icalendar.Component, zone: ZoneInfo, day_bounds: DayBounds
) -> BusyPeriod | None:
    """The event's [start, end) in UTC seconds; None when it has no length."""

    start: object = moment_of(event, "DTSTART")
    end: object = moment_of(event, "DTEND")
    if isinstance(start, datetime.datetime):
        if not isinstance(end, datetime.datetime):
            end = start + duration_of(event)
        return new_period(utc_seconds(start, zone), utc_seconds(end, zone))

    if isinstance(start, datetime.date):
        last: datetime.date = (
            end
            if isinstance(end, datetime.date) and not isinstance(end, datetime.datetime)
            else start + max(duration_of(event), ONE_DAY)
        )
        first_second, end_second = day_bounds(start, last)
        return new_period(first_second, end_second)

    return None


def moment_of(event: icalendar.Component, name: str) -> object:
    value: object = event.get(name)
    return getattr(value, "dt", None)


def duration_of(event: icalendar.Component) -> datetime.timedelta:
    length: object = moment_of(event, "DURATION")
    return length if isinstance(length, datetime.timedelta) else datetime.timedelta(0)


def utc_seconds(moment: datetime.datetime, zone: ZoneInfo) -> int:
    """A zoned moment as is; a floating one in the business's zone."""

    zoned: datetime.datetime = (
        moment if moment.tzinfo is not None else moment.replace(tzinfo=zone)
    )
    return int(zoned.timestamp())
