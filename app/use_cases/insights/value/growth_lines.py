"""
The value model's growth lines: of the bookings kept in a period, those
the waitlist filled and those a rebooking campaign brought back, each with
its value in the business currency.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.campaign_repositories import (
    OriginBookingCountRepoContract,
)
from app.schemas.constants.bookings import BookingOrigin
from app.schemas.dto.growth.growth_counts import OriginBookingCount
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import BookedValueMinor
from app.use_cases.insights.dashboard_values import EARNING_STATUSES


@dataclass(frozen=True)
class GrowthLine:
    """The kept bookings of one origin and their value (None: none had one)."""

    count: PeriodItemCount
    value_minor: BookedValueMinor | None


def count_growth_lines(
    repo: OriginBookingCountRepoContract,
    business_id: BusinessId,
    start: Microseconds,
    end: Microseconds,
    currency_code: CurrencyCode,
) -> dict[BookingOrigin, GrowthLine]:
    """Every origin's line; a cancelled or missed booking is not kept."""

    groups: list[OriginBookingCount] = repo.count_by_origin(business_id, start, end)
    return {
        origin: fold_line(
            [
                group
                for group in groups
                if group.origin is origin and group.status in EARNING_STATUSES
            ],
            currency_code,
        )
        for origin in BookingOrigin
    }


def fold_line(
    groups: list[OriginBookingCount], currency_code: CurrencyCode
) -> GrowthLine:
    priced: list[OriginBookingCount] = [
        group for group in groups if group.currency_code == currency_code
    ]
    value: int = sum(int(group.value_minor) for group in priced)
    return GrowthLine(
        count=PeriodItemCount(sum(int(group.count) for group in groups)),
        value_minor=BookedValueMinor(value) if priced and value > 0 else None,
    )
