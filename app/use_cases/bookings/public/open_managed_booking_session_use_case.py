from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import ManagedBookingRefusalCode
from app.schemas.dto.booking_manage import (
    BookingManageClaims,
    ManagedBookingAction,
    ManagedBookingSession,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import (
    ManagedBookingPages,
    refusal,
)
from app.utilities.bookings.manage_rate_limits import ManageRateLimits

MICROSECONDS_PER_SECOND: int = 1_000_000
# How long the page's credential opens the booking.
SESSION_SECONDS: int = 30 * 60
INVALID_MESSAGE: str = "This booking link is not valid. Check the link."
# A page opens one credential per load: a few a minute at most.
MANAGE_SESSION_LIMITS: ManageRateLimits = ManageRateLimits(
    key_prefix="booking-manage-session",
    per_booking_per_minute=10,
    per_address_per_minute=60,
    per_platform_per_minute=10_000,
    refusal="Too many requests; try again in a minute.",
)


class OpenManagedBookingSessionUseCase(
    UseCaseContract[ManagedBookingAction, ManagedBookingSession]
):
    """
    The booking page trades its link's long-lived token for a short-lived
    credential of the same booking (about 30 minutes, never past the
    link's own expiry), so it can take the token out of the address bar.
    Every route of the page accepts the credential in place of the token,
    and every answer to it carries a credential that ends no later. Only a
    link opens one: a credential cannot be traded for a fresh credential
    (`link_invalid`), and a link of a booking moved since is not found
    (`booking_changed`). Limited per link, per network and for the
    platform.
    """

    def __init__(self, pages: ManagedBookingPages) -> None:
        self._pages: ManagedBookingPages = pages

    def run(self, input_data: ManagedBookingAction) -> ManagedBookingSession:
        if input_data.claims.is_page_session:
            raise NotFoundError(
                INVALID_MESSAGE,
                reasons=refusal(
                    ManagedBookingRefusalCode.LINK_INVALID, INVALID_MESSAGE
                ),
            )

        self._pages.refuse_too_frequent(input_data, MANAGE_SESSION_LIMITS)
        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        now: Microseconds = self._pages.wall_clock.now_unix()
        # Whole seconds, as the credential carries it.
        ends_seconds: int = (
            min(
                int(now) + SESSION_SECONDS * MICROSECONDS_PER_SECOND,
                int(input_data.claims.expires_at),
            )
            // MICROSECONDS_PER_SECOND
        )
        session_claims = BookingManageClaims(
            business_id=input_data.claims.business_id,
            booking_id=input_data.claims.booking_id,
            booking_version=guest_booking.booking.starts_at,
            expires_at=Microseconds(ends_seconds * MICROSECONDS_PER_SECOND),
            is_page_session=True,
        )
        return ManagedBookingSession(
            token=self._pages.token_for(guest_booking.booking, session_claims),
            expires_at=session_claims.expires_at,
        )
