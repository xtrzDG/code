"""
The bookings a business's rule writes about now, one message per booking:
the visits that ended the rule's days ago (an invitation back, a recall),
or the arrivals the rule's days ahead (a pre-arrival note).
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerHistoryRepoContract,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.campaigns import RebookingRuleKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.campaigns import CampaignSettingsDocument
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

MICROSECONDS_PER_SECOND: int = 1_000_000
SECONDS_PER_DAY: int = 24 * 60 * 60
# A visit that became due while the worker was down is still written
# about for three days; later it is left alone.
LATE_DAYS: int = 3
# A pre-arrival note needs half a day before the arrival to be of use.
MIN_NOTICE_SECONDS: int = 12 * 60 * 60
VISITED_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)
GONE_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CANCELLED, BookingStatus.NO_SHOW}
)
# A customer's latest bookings looked at to tell whether they came back.
LATEST_BOOKINGS_LIMIT: DocumentQueryLimit = DocumentQueryLimit(5)


def due_bookings(
    booking_repo: BookingRepoContract,
    settings: CampaignSettingsDocument,
    now: Microseconds,
) -> list[BookingDocument]:
    """The bookings the rule writes about now (no test bookings)."""

    now_seconds: int = int(now) // MICROSECONDS_PER_SECOND
    delay_seconds: int = int(settings.delay_days) * SECONDS_PER_DAY
    if settings.rule_kind is RebookingRuleKind.PRE_ARRIVAL:
        return [
            booking
            for booking in booking_repo.list_ending_after(
                settings.business_id, BookingSearchBoundSeconds(now_seconds)
            )
            if booking.status is BookingStatus.CONFIRMED
            and not booking.is_sandbox
            and now_seconds + MIN_NOTICE_SECONDS
            <= int(booking.starts_at)
            <= now_seconds + delay_seconds
        ]

    due_by: int = max(now_seconds - delay_seconds, 0)
    return [
        booking
        for booking in booking_repo.list_ending_between(
            settings.business_id,
            BookingSearchBoundSeconds(max(due_by - LATE_DAYS * SECONDS_PER_DAY, 0)),
            BookingSearchBoundSeconds(due_by),
        )
        if booking.status in VISITED_STATUSES and not booking.is_sandbox
    ]


def came_back(
    history_repo: CustomerHistoryRepoContract,
    business_id: BusinessId,
    visit: BookingDocument,
) -> bool:
    """The customer booked again after this visit (nothing to invite them to)."""

    later: Sequence[BookingDocument] = history_repo.latest_bookings_of(
        business_id, [visit.contact_id], LATEST_BOOKINGS_LIMIT
    )
    return any(
        booking.id != visit.id
        and int(booking.starts_at) > int(visit.starts_at)
        and booking.status not in GONE_STATUSES
        for booking in later
    )
