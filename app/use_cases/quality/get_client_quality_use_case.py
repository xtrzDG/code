"""The platform admin's view of a client's production quality."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.quality_repositories import (
    ConversationQualityRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.dto.quality import ClientQualityView, QualityDayView, QualityTotals
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.quality.constrained_integers import QualityDropPercent
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.quality.quality_trend import (
    QUALITY_DROP_FLOOR,
    QUALITY_DROP_PERCENT,
    add_totals,
    average_of,
    drop_percent,
    to_sample_view,
)
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    microseconds_to_seconds,
    to_local_moment,
)

TREND_DAYS: int = 30
WEEK_DAYS: int = 7
LOWEST_LISTED: DocumentQueryLimit = DocumentQueryLimit(5)


class GetClientQualityUseCase(UseCaseContract[AdminClientQuery, ClientQualityView]):
    """
    A client's production quality for the platform admin (Clients → the
    client): the judge's daily average over the last 30 days of the
    business's own time zone, the last 7 days against the 7 before (a drop
    by more than the QUALITY_DROP alert's percent, both weeks holding its
    volume floor, is flagged) and the five lowest scores. Scores and
    dates only, no customer text, so the view is not audited.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        conversation_quality_repo: ConversationQualityRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._quality_repo: ConversationQualityRepoContract = conversation_quality_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminClientQuery) -> ClientQualityView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_CLIENTS,
            )
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        until: Microseconds = Microseconds(int(now) + 1)
        day_starts: list[Microseconds] = trend_day_starts(business, now)
        days: list[QualityTotals] = self._quality_repo.sum_days(
            business.id, day_starts, until
        )
        last_week: QualityTotals = add_totals(days[-WEEK_DAYS:])
        previous_week: QualityTotals = add_totals(days[-2 * WEEK_DAYS : -WEEK_DAYS])
        dropped: QualityDropPercent = drop_percent(last_week, previous_week)
        return ClientQualityView(
            business_id=business.id,
            sample_count=add_totals(days).sample_count,
            average_score=average_of(add_totals(days)),
            last_week_average=average_of(last_week),
            previous_week_average=average_of(previous_week),
            drop_percent=dropped,
            is_dropping=(
                min(int(last_week.sample_count), int(previous_week.sample_count))
                >= QUALITY_DROP_FLOOR
                and int(dropped) > QUALITY_DROP_PERCENT
            ),
            days=[
                QualityDayView(
                    day_start=start,
                    sample_count=totals.sample_count,
                    average_score=average_of(totals),
                )
                for start, totals in zip(day_starts, days, strict=True)
            ],
            lowest=[
                to_sample_view(score)
                for score in self._quality_repo.list_lowest(
                    business.id,
                    ActivityWindow(since=day_starts[0], until=until),
                    LOWEST_LISTED,
                )
            ],
        )


def trend_day_starts(
    business: BusinessDocument, now: Microseconds
) -> list[Microseconds]:
    """The starts of the last 30 local days of the business, today last."""

    zone: ZoneInfo = load_time_zone(business.timezone)
    today: date = to_local_moment(microseconds_to_seconds(int(now)), zone).date()
    return [
        Microseconds(local_day_start_microseconds(today - timedelta(days=back), zone))
        for back in range(TREND_DAYS - 1, -1, -1)
    ]
