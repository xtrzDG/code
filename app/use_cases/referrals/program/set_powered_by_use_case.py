from typed_time_provider import Microseconds, WallClock

from app.contracts.referrals import ReferralLinksFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.referrals import POWERED_BY_SOURCE_TAG
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.referrals.program import PoweredByCommand, PoweredByView
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.use_cases.referrals.program.program_views import build_powered_by_view
from app.utilities.referrals.referral_links import can_hide_powered_by

PLAN_REQUIRED_REASON: ErrorReasonCode = ErrorReasonCode("plan_required")


class SetPoweredByUseCase(UseCaseContract[PoweredByCommand, PoweredByView]):
    """
    PUT /v1/businesses/{business_id}/referrals/powered-by (owners): a Plus
    owner leaves the "Powered by" link off their chat, hosted page and
    table card, or brings it back. Another plan answers 409 with reason
    `plan_required` (showing it again is always allowed). The choice is
    kept when the business leaves Plus, but counts only on Plus.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        business_repo: BusinessRepoContract,
        referral_links: ReferralLinksFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._links: ReferralLinksFacilitatorContract = referral_links
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PoweredByCommand) -> PoweredByView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        is_hidden: bool = input_data.request.is_hidden
        if is_hidden and not can_hide_powered_by(business):
            raise ConflictError(
                "Only the Plus plan can leave the Powered by link off.",
                reasons=[
                    ErrorReason(
                        code=PLAN_REQUIRED_REASON,
                        message=ErrorReasonMessage("Switch to the Plus plan first."),
                    )
                ],
            )

        now: Microseconds = self._wall_clock.now_unix()

        def choose(current: BusinessDocument) -> None:
            current.hides_powered_by = is_hidden
            current.updated_at = now

        stored: BusinessDocument = self._business_repo.update(business.id, choose)
        return build_powered_by_view(
            stored, self._links.powered_by_link(stored, POWERED_BY_SOURCE_TAG)
        )
