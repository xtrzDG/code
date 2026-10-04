"""
The money estimate of a value period: the assistant's bookings at their
own values where they have one, the others at the average check.

Values count in the business currency only (items are priced in it); a
booking valued in another currency is counted as one without a value.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from app.schemas.constants.value import RevenueSource, ValueBasis
from app.schemas.dto.operations.activity_counts import BookingValueCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    BookedValueMinor,
    EstimatedRevenueMinor,
)
from app.use_cases.insights.dashboard_values import EARNING_STATUSES


@dataclass(frozen=True)
class BookedMoney:
    """The assistant's earning bookings that carry a value, and what they are worth."""

    count: int
    value_minor: int


@dataclass(frozen=True)
class MoneyEstimate:
    estimated_revenue_minor: EstimatedRevenueMinor | None
    booked_value_minor: BookedValueMinor | None
    revenue_source: RevenueSource | None


def assistant_booked_money(
    made: Sequence[BookingValueCount],
    made_by_staff: Sequence[BookingValueCount],
    currency_code: CurrencyCode,
) -> BookedMoney:
    """The valued earning bookings made in conversations, in the business currency."""

    counts: Counter[str] = Counter()
    values: Counter[str] = Counter()
    for sign, groups in ((1, made), (-1, made_by_staff)):
        for group in groups:
            if group.currency_code != currency_code:
                continue

            if group.status in EARNING_STATUSES:
                counts["all"] += sign * int(group.count)
                values["all"] += sign * int(group.value_minor)

    return BookedMoney(count=max(counts["all"], 0), value_minor=max(values["all"], 0))


def estimate_money(
    basis: ValueBasis,
    earning_units: int,
    booked: BookedMoney,
    average_check: AverageCheckMinor | None,
) -> MoneyEstimate:
    """
    Bookings: their own values plus the others at the average check
    (MIXED), their own values alone when every booking has one or no check
    is known (BOOKED_VALUES), else the check alone (AVERAGE_CHECK).
    Requests: the check alone. None when nothing prices them.
    """

    if basis is ValueBasis.REQUESTS or booked.count == 0:
        if average_check is None:
            return MoneyEstimate(None, None, None)

        return MoneyEstimate(
            EstimatedRevenueMinor(earning_units * int(average_check)),
            None,
            RevenueSource.AVERAGE_CHECK,
        )

    unvalued: int = max(earning_units - booked.count, 0)
    if unvalued == 0 or average_check is None:
        return MoneyEstimate(
            EstimatedRevenueMinor(booked.value_minor),
            BookedValueMinor(booked.value_minor),
            RevenueSource.BOOKED_VALUES,
        )

    return MoneyEstimate(
        EstimatedRevenueMinor(booked.value_minor + unvalued * int(average_check)),
        BookedValueMinor(booked.value_minor),
        RevenueSource.MIXED,
    )
