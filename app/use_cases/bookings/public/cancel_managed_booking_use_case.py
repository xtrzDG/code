from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.booking_manage import ManagedBookingAction, ManagedBookingView
from app.schemas.dto.bookings import BookingResult, CancelBookingCommand
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.utilities.bookings.manage_rate_limits import MANAGE_CHANGE_LIMITS


class CancelManagedBookingUseCase(
    UseCaseContract[ManagedBookingAction, ManagedBookingView]
):
    """
    The guest cancels their booking on its manage page. It is a customer
    request for the guest's own booking, under the same rules as cancelling
    in the chat (`CancelBookingUseCase` with the booking's contact: staff
    are notified, the calendar follows), and only while the booking is
    active, has not started and still starts when the link says (checked
    under the business lock). Cancelling twice is harmless.
    """

    def __init__(
        self,
        pages: ManagedBookingPages,
        cancel_booking: UseCaseContract[CancelBookingCommand, BookingResult],
    ) -> None:
        self._pages: ManagedBookingPages = pages
        self._cancel_booking: UseCaseContract[CancelBookingCommand, BookingResult] = (
            cancel_booking
        )

    def run(self, input_data: ManagedBookingAction) -> ManagedBookingView:
        self._pages.refuse_too_frequent(input_data, MANAGE_CHANGE_LIMITS)
        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        booking = guest_booking.booking
        if not self._is_cancelled_already(guest_booking):
            self._pages.refuse_unchangeable(booking)
            self._cancel_booking.run(
                CancelBookingCommand(
                    business_id=booking.business_id,
                    booking_id=booking.id,
                    contact_id=booking.contact_id,
                    language=booking.language
                    or guest_booking.business.default_language,
                    is_sandbox=False,
                    expected_starts_at=input_data.claims.booking_version,
                )
            )

        cancelled: GuestBooking = self._pages.current(input_data.claims)
        return self._pages.view(cancelled, self._pages.token_for(cancelled.booking))

    @staticmethod
    def _is_cancelled_already(guest_booking: GuestBooking) -> bool:
        return guest_booking.booking.status is BookingStatus.CANCELLED
