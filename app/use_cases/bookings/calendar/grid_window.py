"""
The bookings a calendar window shows: those that start in it, and those
carried into it from before (a stay that began last week, a dinner over
midnight). Each is an index range read bounded on both sides, so the
cost follows the window and the bookings ahead, never the business's
whole history; they are read a keyset page at a time up to a ceiling.
"""

from datetime import date, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.booking_grid import BookingWindow
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import (
    BookingGridDayCount,
    BookingGridReadCeiling,
    BookingSearchBoundSeconds,
    NightCount,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.paging.keyset_paging import single_value_position
from app.utilities.scheduling.zoned_time import (
    local_day_start_microseconds,
    microseconds_to_seconds,
    to_local_date,
)

SECONDS_PER_DAY: int = 86_400
# The longest booking there can be: a stay of the most nights, checked out
# late on the day after (a time-slot booking lasts 30 days at most).
LONGEST_BOOKING_SECONDS: int = (int(NightCount.le or 0) + 2) * SECONDS_PER_DAY
PAGE_SIZE: int = 500
READ_CEILING = BookingGridReadCeiling(5_000)


class WindowBounds(NamedTuple):
    """The local days of a window and its UTC bounds in seconds."""

    days: list[date]
    start: int
    end: int


class WindowBookings(NamedTuple):
    """The bookings of a window by start time, and whether some were left out."""

    bookings: list[BookingDocument]
    is_truncated: bool


def window_bounds(
    first_day: date, days: BookingGridDayCount, zone: ZoneInfo
) -> WindowBounds:
    """
    Raises:
        ValidationFailedError: the window runs past the last date a booking
            may have.
    """

    local_days: list[date] = [
        first_day + timedelta(days=offset) for offset in range(int(days))
    ]
    try:
        to_local_date(local_days[-1])
    except ValueError as error:
        raise ValidationFailedError("The calendar runs past the last date.") from error

    return WindowBounds(
        days=local_days,
        start=_day_start(first_day, zone),
        end=_day_start(local_days[-1] + timedelta(days=1), zone),
    )


def read_window_bookings(
    booking_repo: BookingRepoContract,
    business_id: BusinessId,
    bounds: WindowBounds,
    include_sandbox: IsSandboxIncluded,
) -> WindowBookings:
    """Carried-in bookings first (they start earlier), then those of the window."""

    start = BookingSearchBoundSeconds(max(bounds.start, 0))
    carried: WindowBookings = _read_pages(
        booking_repo,
        business_id,
        BookingWindow(
            starts_from=BookingSearchBoundSeconds(
                max(bounds.start - LONGEST_BOOKING_SECONDS, 0)
            ),
            starts_before=start,
            ends_after=start,
            ends_by=BookingSearchBoundSeconds(bounds.start + LONGEST_BOOKING_SECONDS),
            include_sandbox=include_sandbox,
        ),
        int(READ_CEILING),
    )
    if carried.is_truncated:
        return carried

    inside: WindowBookings = _read_pages(
        booking_repo,
        business_id,
        BookingWindow(
            starts_from=start,
            starts_before=BookingSearchBoundSeconds(max(bounds.end, 0)),
            ends_after=start,
            include_sandbox=include_sandbox,
        ),
        int(READ_CEILING) - len(carried.bookings),
    )
    return WindowBookings(
        bookings=[*carried.bookings, *inside.bookings],
        is_truncated=inside.is_truncated,
    )


def _read_pages(
    booking_repo: BookingRepoContract,
    business_id: BusinessId,
    window: BookingWindow,
    ceiling: int,
) -> WindowBookings:
    bookings: list[BookingDocument] = []
    after: KeysetPosition | None = None
    while True:
        page: list[BookingDocument] = booking_repo.page_in_window(
            business_id,
            window,
            KeysetSlice(after=after, limit=KeysetReadLimit(PAGE_SIZE)),
        )
        bookings.extend(page)
        if len(bookings) > ceiling:
            return WindowBookings(bookings=bookings[:ceiling], is_truncated=True)

        if len(page) < PAGE_SIZE:
            return WindowBookings(bookings=bookings, is_truncated=False)

        last: BookingDocument = page[-1]
        after = single_value_position(int(last.starts_at), str(last.id))


def _day_start(local_date: date, zone: ZoneInfo) -> int:
    return microseconds_to_seconds(local_day_start_microseconds(local_date, zone))
