"""
What the bookings of the dashboard period are worth, per currency, and the
part booked while the business was closed: folded from the grouped sums
the database returns (no booking is read).
"""

from collections import Counter
from collections.abc import Iterable

from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.operations.activity_counts import BookingValueCount
from app.schemas.dto.operations.dashboard import BookedValueTotal
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import BookedValueMinor
from app.use_cases.insights.dashboard_timeline import TimelineStretch

# Bookings that still bring money: made, confirmed or done (not cancelled,
# not a no-show).
EARNING_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)


def booked_value_totals(groups: Iterable[BookingValueCount]) -> list[BookedValueTotal]:
    """The value of the earning bookings with a value, per currency (by code)."""

    values: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    for group in groups:
        if group.currency_code is None or group.status not in EARNING_STATUSES:
            continue

        values[str(group.currency_code)] += int(group.value_minor)
        counts[str(group.currency_code)] += int(group.count)

    return [
        BookedValueTotal(
            currency_code=CurrencyCode(currency),
            value_minor=BookedValueMinor(values[currency]),
            booking_count=PeriodItemCount(counts[currency]),
        )
        for currency in sorted(counts)
    ]


def after_hours_groups(
    groups: Iterable[BookingValueCount],
    stretches: list[TimelineStretch],
) -> list[BookingValueCount]:
    """The groups booked in a closed stretch of the weekly hours."""

    return [group for group in groups if not stretches[int(group.segment)].is_open]
