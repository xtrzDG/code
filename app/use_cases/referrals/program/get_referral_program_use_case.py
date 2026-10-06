from typed_time_provider import Microseconds, WallClock

from app.contracts.referrals import ReferralLinksFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.referral_repositories import ReferralRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.referrals import INVITE_SOURCE_TAG, POWERED_BY_SOURCE_TAG
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.referrals import ReferralDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.operations.activity_counts import ActivityPeriod
from app.schemas.dto.referrals.program import ReferralProgramQuery, ReferralProgramView
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.referrals.constrained_integers import ReferredBusinessCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.referrals.program.program_views import build_powered_by_view
from app.utilities.referrals.invite_card import is_invite_card_due

# The invitations an owner's card counts (far more than anyone sends).
MAX_INVITATIONS_COUNTED: DocumentQueryLimit = DocumentQueryLimit(500)


class GetReferralProgramUseCase(
    UseCaseContract[ReferralProgramQuery, ReferralProgramView]
):
    """
    GET /v1/businesses/{business_id}/referrals (owners): the business's own
    invitation ("Invite a business: a month free for both"): its code and
    link, how many businesses signed up by it, how many paid and earned
    both sides their month, and whether the Overview card is due (from the
    tenth booking, sandbox bookings aside); with the state of its "Powered
    by" link. The first call claims the business's code.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        referral_repo: ReferralRepoContract,
        booking_repo: BookingRepoContract,
        referral_links: ReferralLinksFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._referrals: ReferralRepoContract = referral_repo
        self._bookings: BookingRepoContract = booking_repo
        self._links: ReferralLinksFacilitatorContract = referral_links
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ReferralProgramQuery) -> ReferralProgramView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        invited: list[ReferralDocument] = self._referrals.list_invited_by(
            business.id, MAX_INVITATIONS_COUNTED
        )
        bookings_made: PeriodItemCount = self._count_bookings(business)
        return ReferralProgramView(
            code=self._links.business_code(business.id),
            invite_link=self._links.link_for(business.id, INVITE_SOURCE_TAG),
            invited=ReferredBusinessCount(len(invited)),
            paid=ReferredBusinessCount(
                sum(1 for referral in invited if referral.first_paid_at is not None)
            ),
            rewarded=ReferredBusinessCount(
                sum(1 for referral in invited if referral.rewarded_at is not None)
            ),
            bookings_made=bookings_made,
            is_invite_card_due=is_invite_card_due(bookings_made),
            powered_by=build_powered_by_view(
                business, self._links.powered_by_link(business, POWERED_BY_SOURCE_TAG)
            ),
        )

    def _count_bookings(self, business: BusinessDocument) -> PeriodItemCount:
        """Bookings made since the business was created, sandbox aside."""

        now: Microseconds = self._wall_clock.now_unix()
        start: Microseconds = business.created_at
        if int(start) >= int(now):
            return PeriodItemCount(0)

        period = ActivityPeriod(start=start, end=now, segment_starts=(start,))
        return PeriodItemCount(
            sum(
                int(count.count)
                for count in self._bookings.count_made(business.id, period)
            )
        )
