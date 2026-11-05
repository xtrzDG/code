"""The business's calendar as an erasure sees it: what it was asked to forget."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.contracts.calendar_erasure import CalendarGuestErasureFacilitatorContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount


@dataclass
class RecordingCalendarErasure(CalendarGuestErasureFacilitatorContract):
    """Keeps a copy of every booking whose guest it was asked to forget."""

    forgotten: list[BookingDocument] = field(default_factory=list[BookingDocument])

    def forget_guest(self, bookings: Sequence[BookingDocument]) -> ErasedRecordCount:
        self.forgotten.extend(booking.model_copy() for booking in bookings)
        return ErasedRecordCount(len(bookings))
