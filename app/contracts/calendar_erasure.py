"""
The copies of an erased customer's bookings in the business's own
calendar outside the platform (its connected Google Calendar).
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount


class CalendarGuestErasureFacilitatorContract(FacilitatorContract, Protocol):
    def forget_guest(self, bookings: Sequence[BookingDocument]) -> ErasedRecordCount:
        """
        The guest of these bookings (as the erasure left them: no notes, the
        contact erased) leaves the business's calendar: a booking still
        taking its time keeps its event, rewritten without the guest; any
        other booking's event is deleted. How many events changed. Never
        raises: a failure is logged and shown on the calendar connection.
        """
        raise NotImplementedError
