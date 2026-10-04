"""
One keyset page of a business's bookings with the cabinet's filters (local
start dates in the business time zone, status, resource, sandbox, order):
the Bookings list and its CSV export read the same pages.
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.schemas.constants.bookings import BookingOrder, BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.listing_filters import BookingListFilter
from app.schemas.dto.paging import KeysetPosition, PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.keyset_paging import (
    finish_page,
    read_slice,
    single_value_position,
)
from app.utilities.scheduling.zoned_time import (
    local_day_start_microseconds,
    microseconds_to_seconds,
    parse_local_date,
)


def page_bookings(
    booking_repo: BookingRepoContract,
    business_id: BusinessId,
    zone: ZoneInfo,
    page: PageRequest,
    *,
    date_from_text: LocalDate | None,
    date_to_text: LocalDate | None,
    status: BookingStatus | None,
    resource_id: ResourceId | None,
    include_sandbox: IsSandboxIncluded,
    order: BookingOrder,
) -> tuple[list[BookingDocument], PageCursor | None]:
    """
    The page and the next cursor (None after the last page).

    Raises:
        ValidationFailedError: the start date is after the end date, or the
            cursor is broken.
    """

    date_from: date | None = (
        None if date_from_text is None else parse_local_date(date_from_text)
    )
    date_to: date | None = (
        None if date_to_text is None else parse_local_date(date_to_text)
    )
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValidationFailedError("The start date is after the end date.")

    is_latest_first: bool = order is BookingOrder.LATEST_FIRST
    return finish_page(
        booking_repo.page_by_business(
            business_id,
            read_slice(
                page, single_value_position if is_latest_first else earliest_position
            ),
            BookingListFilter(
                starts_from=day_start_seconds(date_from, zone),
                starts_before=day_start_seconds(
                    None if date_to is None else date_to + timedelta(days=1), zone
                ),
                status=status,
                resource_id=resource_id,
                include_sandbox=include_sandbox,
                order=order,
            ),
        ),
        page,
        # Earliest-first cursors carry the negated start, as they always did.
        sort_key=lambda booking: (
            int(booking.starts_at) if is_latest_first else -int(booking.starts_at)
        ),
        item_id=lambda booking: str(booking.id),
    )


def earliest_position(negated_start: int, item_id: str) -> KeysetPosition:
    """The position of an earliest-first cursor (its key is the negated start)."""

    return single_value_position(-negated_start, item_id)


def day_start_seconds(
    local_date: date | None, zone: ZoneInfo
) -> BookingSearchBoundSeconds | None:
    """UTC seconds when the local date begins (None without a date)."""

    if local_date is None:
        return None

    return BookingSearchBoundSeconds(
        max(microseconds_to_seconds(local_day_start_microseconds(local_date, zone)), 0)
    )
