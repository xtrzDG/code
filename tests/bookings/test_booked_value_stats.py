"""Booked value in the dashboard: per currency, earning bookings, after hours."""

from collections.abc import Sequence
from datetime import datetime

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.operations.activity_counts import BookingValueCount
from app.schemas.dto.operations.dashboard import BookedValueTotal
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    BookingValueMinor,
    PartySize,
)
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    TimelineSegment,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import BookedValueMinor
from app.use_cases.insights.dashboard_values import booked_value_totals
from tests.operations.dashboard_fixture import DashboardFixture
from tests.operations.fakes import to_microseconds


def valued_booking(
    dashboard: DashboardFixture,
    created: str,
    value_minor: int | None,
    currency: str | None = "GEL",
    status: BookingStatus = BookingStatus.CONFIRMED,
    is_sandbox: bool = False,
) -> None:
    moment = to_microseconds(datetime.fromisoformat(created))
    dashboard.world.booking_repo.save(
        BookingDocument(
            business_id=dashboard.business.id,
            resource_id=dashboard.table.id,
            contact_id=dashboard.contact.id,
            starts_at=BookingStartsAtUnixSeconds(1_791_000_000),
            ends_at=BookingEndsAtUnixSeconds(1_791_007_200),
            party_size=PartySize(2),
            status=status,
            source_channel=ChannelKind.WHATSAPP,
            is_sandbox=is_sandbox,
            value_minor=None if value_minor is None else BookingValueMinor(value_minor),
            currency_code=None if currency is None else CurrencyCode(currency),
            created_at=moment,
            updated_at=moment,
        )
    )


def totals(items: Sequence[BookedValueTotal]) -> list[tuple[str, int, int]]:
    return [
        (str(item.currency_code), int(item.value_minor), int(item.booking_count))
        for item in items
    ]


def test_the_dashboard_sums_what_the_period_was_booked_for() -> None:
    dashboard = DashboardFixture()
    # Opening hours are 12:00 to 23:00 in Tbilisi.
    valued_booking(dashboard, "2026-10-02T13:05:00+04:00", 4500)
    valued_booking(dashboard, "2026-10-03T02:05:00+04:00", 80000)
    valued_booking(dashboard, "2026-10-03T23:30:00+04:00", 3000, "USD")
    valued_booking(
        dashboard, "2026-10-04T15:00:00+04:00", 9000, status=BookingStatus.COMPLETED
    )
    # Left out: no value, cancelled, no-show, a test booking, another period.
    valued_booking(dashboard, "2026-10-04T15:05:00+04:00", None, None)
    valued_booking(
        dashboard, "2026-10-04T15:10:00+04:00", 7000, status=BookingStatus.CANCELLED
    )
    valued_booking(
        dashboard, "2026-10-04T15:15:00+04:00", 7000, status=BookingStatus.NO_SHOW
    )
    valued_booking(dashboard, "2026-10-04T15:20:00+04:00", 7000, is_sandbox=True)
    valued_booking(dashboard, "2026-09-20T15:20:00+04:00", 7000)

    stats = dashboard.stats()

    assert totals(stats.booked_value) == [("GEL", 93500, 3), ("USD", 3000, 1)]
    # 02:05 and 23:30 are outside the opening hours.
    assert totals(stats.after_hours_booked_value) == [
        ("GEL", 80000, 1),
        ("USD", 3000, 1),
    ]
    assert stats.booking_count == 7


def test_a_period_without_valued_bookings_shows_no_value() -> None:
    dashboard = DashboardFixture()
    dashboard.booking("2026-10-02T13:05:00+04:00")

    stats = dashboard.stats()

    assert stats.booked_value == []
    assert stats.after_hours_booked_value == []


def test_value_totals_fold_groups_per_currency() -> None:
    def group(
        status: BookingStatus, currency: str | None, count: int, value: int
    ) -> BookingValueCount:
        return BookingValueCount(
            status=status,
            currency_code=None if currency is None else CurrencyCode(currency),
            segment=TimelineSegment(0),
            count=PeriodItemCount(count),
            value_minor=BookedValueMinor(value),
        )

    folded = booked_value_totals(
        [
            group(BookingStatus.CONFIRMED, "EUR", 2, 10000),
            group(BookingStatus.PENDING, "EUR", 1, 2500),
            group(BookingStatus.CANCELLED, "EUR", 4, 99999),
            group(BookingStatus.CONFIRMED, None, 3, 0),
            group(BookingStatus.COMPLETED, "AMD", 1, 500000),
        ]
    )

    assert totals(folded) == [("AMD", 500000, 1), ("EUR", 12500, 3)]
