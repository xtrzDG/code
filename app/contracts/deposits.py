"""What other modules ask of deposits: settling a deposit when its booking ends."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.booleans import IsStaffCancellation
from app.schemas.typings.deposits.prefixed_id import DepositRequestId


class DepositSettlementFacilitatorContract(FacilitatorContract, Protocol):
    def notice_booking_ended(
        self,
        booking: BookingDocument,
        now: Microseconds,
        is_staff_change: IsStaffCancellation = False,
    ) -> None:
        """
        A booking with a deposit was cancelled or its guest did not come: a
        deposit still waiting is CANCELLED (nothing was paid); a paid one is
        settled now, or after the cabinet's undo window for a staff change
        (the sweep settles it). Never raises: the booking change stands.
        """
        raise NotImplementedError

    def settle(
        self,
        business_id: BusinessId,
        request_id: DepositRequestId,
        now: Microseconds,
    ) -> DepositRequestDocument | None:
        """
        Decide a paid deposit whose booking ended: REFUND_DUE (cancelled at
        least the refund cutoff before the start; staff are told to refund
        it), KEPT (cancelled later, or no-show), or still PAID (the booking
        went on after all). None when there was nothing to settle.
        """
        raise NotImplementedError
