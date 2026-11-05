"""The platform's provider spend: today (UTC) by provider, the week before."""

from typed_time_provider import Microseconds

from app.contracts.repositories.spend_guard_repositories import (
    UsageSpendRepoContract,
)
from app.schemas.dto.spend_guard import PlatformSpendFigures, ProviderSpend
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.utilities.spend.spend_days import days_before, utc_day
from app.utilities.spend.spend_pricing import price_usage, total_spend

WEEK_DAYS: int = 7


def read_platform_spend(
    usage_spend_repo: UsageSpendRepoContract, now: Microseconds
) -> PlatformSpendFigures:
    """
    Today's spend from UTC midnight to now, and the 7 whole days before it
    (their daily mean is what the spike alert compares with), each summed by
    the database over the platform's occurred_at index (1142).
    """

    day, started_at = utc_day(now)
    providers: list[ProviderSpend] = price_usage(
        usage_spend_repo.sum_platform(started_at, Microseconds(int(now) + 1))
    )
    week_total: CostMicroUsd = total_spend(
        price_usage(
            usage_spend_repo.sum_platform(
                days_before(started_at, WEEK_DAYS), started_at
            )
        )
    )
    return PlatformSpendFigures(
        day=day,
        providers=providers,
        total_micro_usd=total_spend(providers),
        week_total_micro_usd=week_total,
        week_daily_mean_micro_usd=CostMicroUsd(int(week_total) // WEEK_DAYS),
    )
