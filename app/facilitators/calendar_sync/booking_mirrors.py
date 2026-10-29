from collections.abc import Sequence

from app.contracts.operations import BookingCalendarSyncFacilitatorContract
from app.schemas.domain.bookings import BookingDocument


class BookingMirrors(BookingCalendarSyncFacilitatorContract):
    """
    Every copy of a booking outside the platform, kept in step after each
    change of the booking: the write to its resource's booking system,
    queued first (it never waits for the system), then the event in the
    business's Google Calendar. Never raises: no mirror does.
    """

    def __init__(
        self, mirrors: Sequence[BookingCalendarSyncFacilitatorContract]
    ) -> None:
        self._mirrors: tuple[BookingCalendarSyncFacilitatorContract, ...] = tuple(
            mirrors
        )

    def sync(self, booking: BookingDocument) -> None:
        for mirror in self._mirrors:
            mirror.sync(booking)
