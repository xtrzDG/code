"""Sign-up cohorts by month, and the owners each acquisition source brought."""

from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.analytics.growth_views import CohortRowView, SourceRowView
from app.schemas.typings.analytics.constrained_floats import CohortPayingPercent
from app.schemas.typings.analytics.constrained_integers import OwnerCount
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    CohortMonth,
    ReferralCode,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.analytics.mrr_math import paying_businesses_at
from app.utilities.analytics.owner_journeys import OwnerJourney

MICROSECONDS_PER_SECOND: int = 1_000_000
MONTHS_PER_YEAR: int = 12
# Columns of the cohort grid: the sign-up month and the eleven after it.
MAX_COHORT_MONTHS: int = 12


def month_start(year: int, month: int) -> Microseconds:
    """The first microsecond of a UTC calendar month (month may overflow)."""

    year += (month - 1) // MONTHS_PER_YEAR
    month = (month - 1) % MONTHS_PER_YEAR + 1
    moment = datetime(year, month, 1, tzinfo=UTC)
    return Microseconds(int(moment.timestamp()) * MICROSECONDS_PER_SECOND)


def month_of(at: Microseconds) -> tuple[int, int]:
    moment = datetime.fromtimestamp(int(at) / MICROSECONDS_PER_SECOND, tz=UTC)
    return moment.year, moment.month


def owns_paying_business(journey: OwnerJourney, paying: set[BusinessId]) -> bool:
    return any(business.business_id in paying for business in journey.businesses)


def build_cohorts(
    journeys: Sequence[OwnerJourney],
    billing_events: Sequence[ProductEventDocument],
    now: Microseconds,
) -> list[CohortRowView]:
    """
    One row per sign-up month (oldest first): its owners, those who went
    live, and the share with a paying business at the end of each month
    since, up to twelve months and never past now.
    """

    cohorts: dict[tuple[int, int], list[OwnerJourney]] = defaultdict(list)
    for journey in journeys:
        cohorts[month_of(journey.signed_up_at)].append(journey)

    paying_cache: dict[int, set[BusinessId]] = {}

    def paying_at(at: Microseconds) -> set[BusinessId]:
        if int(at) not in paying_cache:
            paying_cache[int(at)] = paying_businesses_at(billing_events, at)
        return paying_cache[int(at)]

    rows: list[CohortRowView] = []
    for (year, month), members in sorted(cohorts.items()):
        shares: list[CohortPayingPercent] = []
        for offset in range(MAX_COHORT_MONTHS):
            starts = month_start(year, month + offset)
            if int(starts) > int(now):
                break

            ends = month_start(year, month + offset + 1)
            at = Microseconds(min(int(ends) - 1, int(now)))
            paying = sum(
                owns_paying_business(owner, paying_at(at)) for owner in members
            )
            shares.append(CohortPayingPercent(round(100.0 * paying / len(members), 2)))

        rows.append(
            CohortRowView(
                month=CohortMonth(f"{year:04d}-{month:02d}"),
                sign_ups=OwnerCount(len(members)),
                went_live=OwnerCount(
                    sum(
                        journey.reached([ProductEventName.WENT_LIVE]) is not None
                        for journey in members
                    )
                ),
                paying=shares,
            )
        )

    return rows


# An acquisition source and the referral code of its link, if any.
type SourceKey = tuple[AcquisitionSourceKey, ReferralCode | None]


def build_sources(
    journeys: Sequence[OwnerJourney],
    paying_now: set[BusinessId],
) -> list[SourceRowView]:
    """
    Per acquisition source and referral code: sign-ups, owners live and
    paying today; the most sign-ups first.
    """

    sign_ups: Counter[SourceKey] = Counter()
    live: Counter[SourceKey] = Counter()
    paying: Counter[SourceKey] = Counter()
    for journey in journeys:
        key: SourceKey = (journey.source, journey.referral_code)
        sign_ups[key] += 1
        if journey.reached([ProductEventName.WENT_LIVE]) is not None:
            live[key] += 1
        if owns_paying_business(journey, paying_now):
            paying[key] += 1

    return [
        SourceRowView(
            source=key[0],
            referral_code=key[1],
            sign_ups=OwnerCount(count),
            went_live=OwnerCount(live[key]),
            paying=OwnerCount(paying[key]),
        )
        for key, count in sorted(
            sign_ups.items(),
            key=lambda item: (-item[1], str(item[0][0]), str(item[0][1] or "")),
        )
    ]
