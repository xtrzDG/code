from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.booking_manage import ManagedBookingAction, ManagedBookingView
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.utilities.bookings.manage_rate_limits import MANAGE_VIEW_LIMITS


class GetManagedBookingUseCase(
    UseCaseContract[ManagedBookingAction, ManagedBookingView]
):
    """
    The guest's booking for its manage page: when and for how many, the
    service, the address with a map link, the cancellation policy, the
    ways to write to the business and what the guest may still change.
    A link of a booking moved since is not found (`booking_changed`).
    """

    def __init__(self, pages: ManagedBookingPages) -> None:
        self._pages: ManagedBookingPages = pages

    def run(self, input_data: ManagedBookingAction) -> ManagedBookingView:
        self._pages.refuse_too_frequent(input_data, MANAGE_VIEW_LIMITS)
        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        return self._pages.view(
            guest_booking, self._pages.token_for(guest_booking.booking)
        )
