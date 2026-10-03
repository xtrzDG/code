from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.value_repositories import ValueCountRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_views import TodayQueue, TodayQueueQuery
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.use_cases.insights.value.value_access import local_today
from app.utilities.scheduling.zoned_time import (
    MICROSECONDS_PER_SECOND,
    load_time_zone,
    local_day_start_microseconds,
    microseconds_to_seconds,
    to_local_date,
)

ON_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)


class GetTodayQueueUseCase(UseCaseContract[TodayQueueQuery, TodayQueue]):
    """
    Today's bookings for the staff's "Your queue today" (owners and staff):
    how many are on, how many still to start and how many wait for
    confirmation. Two indexed counts by start time; counts only, so no
    audit entry.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        value_count_repo: ValueCountRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._value_count_repo: ValueCountRepoContract = value_count_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: TodayQueueQuery) -> TodayQueue:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        today: date = local_today(business, self._wall_clock)
        day_start: int = (
            local_day_start_microseconds(today, zone) // MICROSECONDS_PER_SECOND
        )
        day_end: int = (
            local_day_start_microseconds(today + timedelta(days=1), zone)
            // MICROSECONDS_PER_SECOND
        )
        now: int = microseconds_to_seconds(int(self._wall_clock.now_unix()))
        whole_day = self._value_count_repo.count_bookings_starting(
            business.id,
            BookingSearchBoundSeconds(day_start),
            BookingSearchBoundSeconds(day_end),
        )
        still_to_start = self._value_count_repo.count_bookings_starting(
            business.id,
            BookingSearchBoundSeconds(min(max(now, day_start), day_end)),
            BookingSearchBoundSeconds(day_end),
        )
        return TodayQueue(
            business_id=business.id,
            date=to_local_date(today),
            booking_count=on_count(whole_day),
            upcoming_booking_count=on_count(still_to_start),
            unconfirmed_booking_count=PeriodItemCount(
                int(still_to_start.get(BookingStatus.PENDING, 0))
            ),
        )


def on_count(counts: dict[BookingStatus, PeriodItemCount]) -> PeriodItemCount:
    return PeriodItemCount(
        sum(int(count) for status, count in counts.items() if status in ON_STATUSES)
    )
