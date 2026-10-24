from typed_time_provider import Microseconds, WallClock

from app.contracts.booking_links import BookingManageTokenSignerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import ManagedBookingRefusalCode
from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.use_cases.bookings.public.managed_booking_pages import refusal

INVALID_MESSAGE: str = "This booking link is not valid. Check the link."
EXPIRED_MESSAGE: str = "This booking link has expired."


class OpenBookingManageLinkUseCase(
    UseCaseContract[BookingManageToken, BookingManageClaims]
):
    """
    Check a guest's manage link before anything is read: the platform must
    have signed it (with the current key of ENCRYPTION_KEYS or a previous
    one) and it must not have expired. Its claims name the business whose
    storage scope the request then enters. A forged, altered or expired
    link is not found (reasons `link_invalid`, `link_expired`), so the
    answer never tells a guesser more.
    """

    def __init__(
        self,
        link_signer: BookingManageTokenSignerContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._link_signer: BookingManageTokenSignerContract = link_signer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BookingManageToken) -> BookingManageClaims:
        claims: BookingManageClaims | None = self._link_signer.read(input_data)
        if claims is None:
            raise NotFoundError(
                INVALID_MESSAGE,
                reasons=refusal(
                    ManagedBookingRefusalCode.LINK_INVALID, INVALID_MESSAGE
                ),
            )

        if self._wall_clock.now_unix() >= claims.expires_at:
            raise NotFoundError(
                EXPIRED_MESSAGE,
                reasons=refusal(
                    ManagedBookingRefusalCode.LINK_EXPIRED, EXPIRED_MESSAGE
                ),
            )

        return claims
