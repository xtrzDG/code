"""
Where the value and dashboard periods of a business may start: not before
it went live, nor (live before its milestones were kept, or not live yet)
before it was created. A period asked for from earlier days starts on that
day instead, so a business launched today reads "since today", never as a
month of zeros before it existed.
"""

from dataclasses import dataclass
from datetime import date

from typed_time_provider import Microseconds

from app.contracts.repositories.setup_repositories import ActivationEventRepoContract
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import ActivationEventDocument
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)
from app.utilities.value.value_periods import ValueDates, days_before


@dataclass(frozen=True)
class LaunchFloor:
    """
    When the business first went live (None: not yet, or before milestones
    were kept) and the first local day its periods may count.
    """

    went_live_at: Microseconds | None
    first_day: date


def read_launch_floor(
    activation_event_repo: ActivationEventRepoContract, business: BusinessDocument
) -> LaunchFloor:
    """The business's WENT_LIVE milestone, else its creation, as a local day."""

    events: list[ActivationEventDocument] = activation_event_repo.list_by_business(
        business.id
    )
    went_live_at: Microseconds | None = next(
        (
            event.occurred_at
            for event in events
            if event.kind is ActivationEventKind.WENT_LIVE
        ),
        None,
    )
    moment: Microseconds = business.created_at if went_live_at is None else went_live_at
    first_day: date = to_local_moment(
        microseconds_to_seconds(int(moment)), load_time_zone(business.timezone)
    ).date()
    return LaunchFloor(went_live_at=went_live_at, first_day=first_day)


def floored_start(date_from: date, date_to: date, floor: LaunchFloor) -> date:
    """
    The later of `date_from` and the floor's first day, never after
    `date_to` (a period that ended before the floor keeps its last day).
    """

    return min(max(date_from, floor.first_day), date_to)


def floored_dates(dates: ValueDates, floor: LaunchFloor) -> ValueDates:
    """
    The dates with their start moved up to the floor, compared with as many
    days before them; unchanged when they start on or after it.
    """

    start: date = floored_start(dates.date_from, dates.date_to, floor)
    return dates if start == dates.date_from else days_before(start, dates.date_to)
