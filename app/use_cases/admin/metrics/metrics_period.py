"""The days the founder's metrics cover: UTC calendar days, both included."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from typed_time_provider import Microseconds

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.analytics.constrained_strings import MetricsDate

MICROSECONDS_PER_SECOND: int = 1_000_000
DEFAULT_PERIOD_DAYS: int = 90
# Two years of sign-ups at most: the metrics read the period's events.
MAX_PERIOD_DAYS: int = 731


@dataclass(frozen=True)
class MetricsPeriod:
    """The first and the last day, and the period as [start, end) in time."""

    first_day: MetricsDate
    last_day: MetricsDate
    start: Microseconds
    end: Microseconds


def to_microseconds(day: date) -> Microseconds:
    midnight = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return Microseconds(int(midnight.timestamp()) * MICROSECONDS_PER_SECOND)


def calendar_day(day: MetricsDate) -> date:
    """The day itself; a day the calendar does not have (02-30) is invalid."""

    try:
        return date.fromisoformat(str(day))
    except ValueError as error:
        raise ValidationFailedError(f"{day} is not a calendar day.") from error


def resolve_period(
    first: MetricsDate | None,
    last: MetricsDate | None,
    now: Microseconds,
) -> MetricsPeriod:
    """
    The asked days; without them the last 90 days up to today, and a
    missing first day 90 days before the last one.

    Raises:
        ValidationFailedError: a day the calendar does not have, the first
            day after the last one, or a period longer than two years.
    """

    today: date = datetime.fromtimestamp(int(now) / MICROSECONDS_PER_SECOND, UTC).date()
    last_day: date = today if last is None else calendar_day(last)
    first_day: date = (
        last_day - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
        if first is None
        else calendar_day(first)
    )
    if first_day > last_day:
        raise ValidationFailedError("The period must start before it ends.")

    if (last_day - first_day).days + 1 > MAX_PERIOD_DAYS:
        raise ValidationFailedError(
            f"A period of at most {MAX_PERIOD_DAYS} days can be shown at once."
        )

    return MetricsPeriod(
        first_day=MetricsDate(first_day.isoformat()),
        last_day=MetricsDate(last_day.isoformat()),
        start=to_microseconds(first_day),
        end=to_microseconds(last_day + timedelta(days=1)),
    )
