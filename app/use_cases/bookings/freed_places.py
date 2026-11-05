"""
A booking change that gives up a place (a cancellation, a move, a change of
resource, a status that no longer takes a unit) tells the waitlist, which
offers the place to the first waiting customer who fits.
"""

from typed_time_provider import Microseconds

from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.typings.waitlist.booleans import IsStaffBookingChange
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES


def held_place_of(booking: BookingDocument) -> FreedPlace | None:
    """The place a booking takes now; None when its status takes none."""

    if booking.status not in BLOCKING_BOOKING_STATUSES or booking.is_sandbox:
        return None

    return FreedPlace(
        freed_booking_id=booking.id,
        resource_id=booking.resource_id,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
    )


def notice_if_freed(
    growth: GrowthBookingsFacilitatorContract,
    before: FreedPlace | None,
    booking: BookingDocument,
    now: Microseconds,
    is_staff_change: IsStaffBookingChange,
) -> None:
    """Tell the waitlist when the place taken `before` the change is free now."""

    if before is None or held_place_of(booking) == before:
        return

    growth.notice_freed(booking, before, now, is_staff_change)
