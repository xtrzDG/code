from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.staff_links import (
    StaffLinkClaims,
    StaffLinkQuery,
    StaffLinkView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    to_local_date,
    to_local_moment,
)


class ResolveStaffLinkUseCase(UseCaseContract[StaffLinkQuery, StaffLinkView]):
    """
    A signed-in member opens a notification link: the page it leads to
    when the platform signed it for this business and it has not expired
    (7 days). An expired link says so and names no page. A forged or
    foreign link is not found. Every page checks access again.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        link_signer: StaffLinkSignerContract,
        booking_repo: BookingRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._link_signer: StaffLinkSignerContract = link_signer
        self._booking_repo: BookingRepoContract = booking_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StaffLinkQuery) -> StaffLinkView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        claims: StaffLinkClaims | None = self._link_signer.read(input_data.token)
        if claims is None or claims.business_id != business.id:
            raise NotFoundError("This link is not valid.")

        if claims.expires_at <= self._wall_clock.now_unix():
            return StaffLinkView(
                business_id=business.id,
                target=claims.target,
                expires_at=claims.expires_at,
                is_expired=True,
            )

        return StaffLinkView(
            business_id=business.id,
            target=claims.target,
            conversation_id=claims.conversation_id,
            lead_id=claims.lead_id,
            booking_id=claims.booking_id,
            booking_date=self._booking_date(business, claims),
            expires_at=claims.expires_at,
        )

    def _booking_date(
        self,
        business: BusinessDocument,
        claims: StaffLinkClaims,
    ) -> LocalDate | None:
        """The local day of a booking, so the bookings page opens on it."""

        if claims.target is not StaffLinkTarget.BOOKING or claims.booking_id is None:
            return None

        booking: BookingDocument | None = self._booking_repo.get(
            business.id, claims.booking_id
        )
        if booking is None:
            return None

        zone: ZoneInfo = load_time_zone(business.timezone)
        return to_local_date(to_local_moment(int(booking.starts_at), zone).date())
