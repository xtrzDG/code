"""Whether a business is open at a local moment (for the after-hours flag)."""

from datetime import date, datetime, timedelta

from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument

MINUTES_PER_HOUR: int = 60
MINUTES_PER_DAY: int = 24 * MINUTES_PER_HOUR


def is_open_at(
    local_moment: datetime,
    hours: list[OpeningInterval],
    business_exceptions: list[ScheduleExceptionDocument],
) -> bool | None:
    """
    True or False for a moment in the business time zone; None when the
    profile has no opening hours.

    Business-wide exceptions replace a day's hours (closed all day, or
    special hours). An interval closing at or before its opening time runs
    past midnight into the next day.
    """

    if not hours:
        return None

    minute_of_day: int = local_moment.hour * MINUTES_PER_HOUR + local_moment.minute
    today: date = local_moment.date()
    yesterday: date = today - timedelta(days=1)
    for interval in intervals_on(today, hours, business_exceptions):
        opens_at, closes_at = int(interval.opens_at), int(interval.closes_at)
        if closes_at <= opens_at:
            if minute_of_day >= opens_at:
                return True
        elif opens_at <= minute_of_day < closes_at:
            return True

    for interval in intervals_on(yesterday, hours, business_exceptions):
        opens_at, closes_at = int(interval.opens_at), int(interval.closes_at)
        if closes_at <= opens_at and minute_of_day < closes_at:
            return True

    return False


def intervals_on(
    day: date,
    hours: list[OpeningInterval],
    business_exceptions: list[ScheduleExceptionDocument],
) -> list[OpeningInterval]:
    """Opening intervals of one local date after holidays and special hours."""

    for exception in business_exceptions:
        if exception.resource_id is not None or str(exception.date) != day.isoformat():
            continue

        if exception.is_closed_all_day:
            return []

        return [
            interval
            for interval in exception.special_hours
            if int(interval.weekday) == day.isoweekday()
        ] or list(exception.special_hours)

    return [interval for interval in hours if int(interval.weekday) == day.isoweekday()]
