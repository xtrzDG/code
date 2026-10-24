import logging

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingConfirmationChange
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
    ManagedBookingAction,
    ManagedBookingView,
)
from app.schemas.dto.bookings import BookingResult, RescheduleBookingCommand
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.utilities.bookings.manage_rate_limits import MANAGE_CHANGE_LIMITS

logger: logging.Logger = logging.getLogger(__name__)
DATE_REQUIRED_MESSAGE: str = "Give the new date of the booking."


class RescheduleManagedBookingUseCase(
    UseCaseContract[ManagedBookingAction, ManagedBookingView]
):
    """
    The guest moves their booking on its manage page to a time
    `check_availability` offered. It is a customer request for the guest's
    own booking, under the same rules as moving it in the chat
    (`RescheduleBookingUseCase` with the booking's contact: the online
    notice applies, the place is re-checked under the business lock, staff
    are notified). Only an active, upcoming booking that still starts when
    the link says can move, so two tabs of one link cannot both move it.

    The moved booking gets a new link (the page continues under it) and
    the chat it was made in gets the new confirmation.
    """

    def __init__(
        self,
        pages: ManagedBookingPages,
        reschedule_booking: UseCaseContract[RescheduleBookingCommand, BookingResult],
        send_confirmation: UseCaseContract[
            BookingConfirmationRequest, BookingConfirmationReceipt
        ],
    ) -> None:
        self._pages: ManagedBookingPages = pages
        self._reschedule_booking: UseCaseContract[
            RescheduleBookingCommand, BookingResult
        ] = reschedule_booking
        self._send_confirmation: UseCaseContract[
            BookingConfirmationRequest, BookingConfirmationReceipt
        ] = send_confirmation

    def run(self, input_data: ManagedBookingAction) -> ManagedBookingView:
        self._pages.refuse_too_frequent(input_data, MANAGE_CHANGE_LIMITS)
        if input_data.date is None:
            raise ValidationFailedError(DATE_REQUIRED_MESSAGE)

        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        booking = guest_booking.booking
        self._pages.refuse_unchangeable(booking)
        self._reschedule_booking.run(
            RescheduleBookingCommand(
                business_id=booking.business_id,
                booking_id=booking.id,
                contact_id=booking.contact_id,
                new_date=input_data.date,
                new_time=input_data.time,
                language=booking.language or guest_booking.business.default_language,
                is_sandbox=False,
                expected_starts_at=input_data.claims.booking_version,
            )
        )
        moved: GuestBooking | None = self._pages.guest_bookings.read(
            booking.business_id, booking.id
        )
        if moved is None:
            raise NotFoundError("The booking was not found.")

        self._confirm(moved)
        return self._pages.view(moved, self._pages.token_for(moved.booking))

    def _confirm(self, moved: GuestBooking) -> None:
        """The new confirmation; a failure leaves the move in place."""

        try:
            self._send_confirmation.run(
                BookingConfirmationRequest(
                    business_id=moved.booking.business_id,
                    booking_id=moved.booking.id,
                    change=BookingConfirmationChange.MOVED,
                )
            )
        except Exception:
            logger.exception(
                "The confirmation of moved booking %s could not be sent.",
                moved.booking.id,
            )
