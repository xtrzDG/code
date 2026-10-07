"""
The local dates a dashboard covers: the last 30 days, at most 366, never
from before the business went live (or was created).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.dto.operations.dashboard import DashboardStatsQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.value.booleans import IsPeriodSinceLaunch
from app.use_cases.insights.value.launch_floor import LaunchFloor, floored_start
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
    to_local_moment,
)

DEFAULT_PERIOD_DAYS: int = 30
MAX_PERIOD_DAYS: int = 366


@dataclass(frozen=True)
class DashboardDates:
    """
    The local dates counted, and whether the start was moved up to the
    floor from an earlier day asked for.
    """

    date_from: date
    date_to: date
    is_since_launch: IsPeriodSinceLaunch


def choose_dashboard_period(
    query: DashboardStatsQuery,
    zone: ZoneInfo,
    now: Microseconds,
    floor: LaunchFloor,
) -> DashboardDates:
    today: date = to_local_moment(microseconds_to_seconds(int(now)), zone).date()
    date_to: date = today if query.date_to is None else parse_local_date(query.date_to)
    date_from: date = (
        date_to - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
        if query.date_from is None
        else parse_local_date(query.date_from)
    )
    if date_from > date_to:
        raise ValidationFailedError("The start date is after the end date.")

    if (date_to - date_from).days + 1 > MAX_PERIOD_DAYS:
        raise ValidationFailedError(
            f"The period may be at most {MAX_PERIOD_DAYS} days long."
        )

    start: date = floored_start(date_from, date_to, floor)
    return DashboardDates(
        date_from=start, date_to=date_to, is_since_launch=start > date_from
    )
