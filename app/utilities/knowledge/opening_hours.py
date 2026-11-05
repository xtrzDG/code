"""Validation of opening intervals (business hours, resource schedules).

Minutes are local to the business time zone. An interval opens at 0..1439
and closes at 1..1440, where 1440 is midnight at the end of the day. Hours
past midnight are a second interval on the next weekday (Fri 18:00-24:00 and
Sat 00:00-02:00), so every interval stays inside one local day.
"""

from collections.abc import Sequence

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.exceptions.application_errors import ValidationFailedError

MAX_INTERVALS_PER_DAY: int = 12


def validate_opening_intervals(
    intervals: Sequence[OpeningInterval],
    subject: str,
) -> list[OpeningInterval]:
    """
    Check intervals and return them sorted by weekday and opening minute.

    `subject` names what is validated in error messages ("opening hours").

    Raises:
        ValidationFailedError: an interval closes before it opens, intervals
            of one weekday overlap, or a day has too many intervals.
    """

    for interval in intervals:
        if interval.closes_at <= interval.opens_at:
            raise ValidationFailedError(
                f"{subject}: on {interval.weekday.name.lower()} the interval "
                f"{format_minute(interval.opens_at)}-"
                f"{format_minute(interval.closes_at)} closes before it opens. "
                "Split hours past midnight into two days (until 24:00, then from "
                "00:00)."
            )

    ordered: list[OpeningInterval] = sorted(
        (interval.model_copy() for interval in intervals),
        key=lambda interval: (interval.weekday, interval.opens_at),
    )
    for weekday in Weekday:
        day_intervals: list[OpeningInterval] = [
            interval for interval in ordered if interval.weekday is weekday
        ]
        if len(day_intervals) > MAX_INTERVALS_PER_DAY:
            raise ValidationFailedError(
                f"{subject}: {weekday.name.lower()} has more than "
                f"{MAX_INTERVALS_PER_DAY} intervals."
            )

        for previous, current in zip(day_intervals, day_intervals[1:], strict=False):
            if current.opens_at < previous.closes_at:
                raise ValidationFailedError(
                    f"{subject}: on {weekday.name.lower()} the intervals "
                    f"{format_minute(previous.opens_at)}-"
                    f"{format_minute(previous.closes_at)} and "
                    f"{format_minute(current.opens_at)}-"
                    f"{format_minute(current.closes_at)} overlap."
                )

    return ordered


def format_minute(minute_of_day: int) -> str:
    """Render a minute of the day as HH:MM (1440 as 24:00)."""

    hours, minutes = divmod(minute_of_day, 60)
    return f"{hours:02d}:{minutes:02d}"
