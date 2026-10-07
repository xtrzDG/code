"""
Reading and recording the booking-system side of a booking: the system its
resource follows, the booking as written there (kept on the booking), and
how a write went (kept on the resource's calendar settings).
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.calendar_sync import (
    BookingSystemConnectorContract,
    ResourceCalendarLinkRepoContract,
)
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar_sync import (
    BookingSystemBookingRef,
    BookingSystemLink,
    ResourceCalendarLinkDocument,
)
from app.schemas.dto.calendar_sync.busy_reads import BookingSystemCredentials
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.calendar_sync.booking_system_writes import (
    write_failed,
    write_succeeded,
)

# One call to a booking system with the resource's key.
type WriteCall = Callable[
    [BookingSystemConnectorContract, BookingSystemCredentials], None
]


def system_of(
    link_repo: ResourceCalendarLinkRepoContract,
    business_id: BusinessId,
    resource_id: ResourceId,
) -> BookingSystemLink | None:
    """The booking system a resource follows, if any."""

    link: ResourceCalendarLinkDocument | None = link_repo.get(business_id, resource_id)
    return None if link is None else link.booking_system


def keep_written(
    booking_repo: BookingRepoContract,
    booking: BookingDocument,
    expected: BookingSystemBookingRef | None,
    written: BookingSystemBookingRef | None,
) -> None:
    """
    Keep what the booking system now holds of the booking, when the stored
    booking still names `expected` (a write never undoes a newer one).
    """

    def keep(current: BookingDocument) -> BookingDocument | None:
        if current.booking_system_booking != expected:
            return None

        return current.model_copy(update={"booking_system_booking": written})

    booking_repo.update(booking.business_id, booking.id, keep)


def record_write(
    link_repo: ResourceCalendarLinkRepoContract,
    business_id: BusinessId,
    resource_id: ResourceId,
    now: Microseconds,
    error: BusyTimeSourceError | None,
) -> None:
    """How a write went, on the resource's settings as stored now."""

    def record(
        current: ResourceCalendarLinkDocument,
    ) -> ResourceCalendarLinkDocument | None:
        system: BookingSystemLink | None = current.booking_system
        if system is None:
            return None

        status = (
            write_succeeded(system.write_status, now)
            if error is None
            else write_failed(system.write_status, now, error.problem, str(error))
        )
        return current.model_copy(
            update={
                "booking_system": system.model_copy(update={"write_status": status}),
                "updated_at": now,
            }
        )

    link_repo.update(business_id, resource_id, record)
