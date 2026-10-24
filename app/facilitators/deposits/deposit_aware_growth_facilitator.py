from typed_time_provider import Microseconds

from app.contracts.deposits import DepositSettlementFacilitatorContract
from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.schemas.constants.bookings import BookingOrigin
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.waitlist.booleans import (
    IsStaffBookingChange,
    IsWaitlistEnabled,
)


class DepositAwareGrowthFacilitator(GrowthBookingsFacilitatorContract):
    """
    The revenue features' side of every booking change, deposits included:
    the waitlist and the campaigns answer as before (`inner`), and a place
    freed by a cancellation or a no-show also settles the booking's
    deposit (`deposits`). Every booking use case that frees a place tells
    this one, so no change of booking is missed and none of them knows
    about deposits.
    """

    def __init__(
        self,
        inner: GrowthBookingsFacilitatorContract,
        deposits: DepositSettlementFacilitatorContract,
    ) -> None:
        self._inner: GrowthBookingsFacilitatorContract = inner
        self._deposits: DepositSettlementFacilitatorContract = deposits

    def held_places(
        self,
        business_id: BusinessId,
        ends_after: BookingSearchBoundSeconds,
        now: Microseconds,
        holder: ContactId | None,
    ) -> list[BookingDocument]:
        return self._inner.held_places(business_id, ends_after, now, holder)

    def is_waitlist_open(self, business_id: BusinessId) -> IsWaitlistEnabled:
        return self._inner.is_waitlist_open(business_id)

    def attribute(
        self, booking: BookingDocument, now: Microseconds
    ) -> BookingOrigin | None:
        return self._inner.attribute(booking, now)

    def notice_freed(
        self,
        booking: BookingDocument,
        place: FreedPlace,
        now: Microseconds,
        is_staff_change: IsStaffBookingChange = False,
    ) -> None:
        self._inner.notice_freed(booking, place, now, is_staff_change)
        self._deposits.notice_booking_ended(booking, now, is_staff_change)
