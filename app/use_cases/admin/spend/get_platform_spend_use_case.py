from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.spend_guard_repositories import (
    SpendLimitMarkRepoContract,
    UsageSpendRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.business_limits import SpendLimitMarkDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.spend_guard import (
    AdminSpendQuery,
    BusinessSpendMark,
    PlatformSpendFigures,
    PlatformSpendView,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.spend.constrained_integers import SpendPercent
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.utilities.spend.platform_spend import read_platform_spend
from app.utilities.spend.spend_days import DAY_MICROSECONDS, utc_day

MAX_BRAKED_BUSINESSES: int = 20


class GetPlatformSpendUseCase(UseCaseContract[AdminSpendQuery, PlatformSpendView]):
    """
    The admin overview's spend tile: the platform's provider spend of the
    current UTC day by provider (recorded costs, planned prices where a
    figure is missing), the daily mean of the 7 days before, the daily
    budget (PLATFORM_DAILY_SPEND_BUDGET_USD) and how much of it is used, and
    the businesses that passed one of their spend limits in the last day
    (their own days: the marks of yesterday, today and tomorrow in UTC
    dates, reached within 24 hours), the latest first.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        usage_spend_repo: UsageSpendRepoContract,
        spend_limit_mark_repo: SpendLimitMarkRepoContract,
        business_repo: BusinessRepoContract,
        settings: SpendGuardSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._usage: UsageSpendRepoContract = usage_spend_repo
        self._marks: SpendLimitMarkRepoContract = spend_limit_mark_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._settings: SpendGuardSettings = settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminSpendQuery) -> PlatformSpendView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_CLIENTS,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        figures: PlatformSpendFigures = read_platform_spend(self._usage, now)
        budget = self._settings.platform_daily_budget_micro_usd
        return PlatformSpendView(
            day=figures.day,
            total_micro_usd=figures.total_micro_usd,
            providers=list(figures.providers),
            week_daily_mean_micro_usd=figures.week_daily_mean_micro_usd,
            budget_micro_usd=None if budget is None else CostMicroUsd(int(budget)),
            budget_used_percent=(
                None
                if budget is None
                else SpendPercent(int(figures.total_micro_usd) * 100 // int(budget))
            ),
            braked_businesses=self._braked_businesses(now),
        )

    def _braked_businesses(self, now: Microseconds) -> list[BusinessSpendMark]:
        marks: list[SpendLimitMarkDocument] = [
            mark
            for day in nearby_days(now)
            for mark in self._marks.list_by_day(day)
            if int(mark.reached_at) > int(now) - DAY_MICROSECONDS
        ]
        marks.sort(key=lambda mark: int(mark.reached_at), reverse=True)
        braked: list[BusinessSpendMark] = []
        for mark in marks[:MAX_BRAKED_BUSINESSES]:
            business: BusinessDocument | None = self._business_repo.get(
                mark.business_id
            )
            if business is not None:
                braked.append(
                    BusinessSpendMark(
                        business_id=business.id,
                        business_name=business.name,
                        level=mark.level,
                        spend_micro_usd=mark.spend_micro_usd,
                        limit_micro_usd=mark.limit_micro_usd,
                        reached_at=mark.reached_at,
                    )
                )

        return braked


def nearby_days(now: Microseconds) -> list[SpendDay]:
    """The UTC dates of yesterday, today and tomorrow: every business's today."""

    return [
        utc_day(Microseconds(int(now) + offset * DAY_MICROSECONDS))[0]
        for offset in (-1, 0, 1)
    ]
