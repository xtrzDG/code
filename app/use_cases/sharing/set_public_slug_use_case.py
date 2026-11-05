from typed_time_provider import Microseconds, WallClock

from app.contracts.referrals import ReferralLinksFacilitatorContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.sharing_repositories import (
    PublicSlugClaimRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.referrals import TABLE_CARD_SOURCE_TAG
from app.schemas.constants.sharing import PublicSlugRefusalCode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.sharing import PublicSlugCommand, ShareLinksView
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.use_cases.sharing.public_slug_claims import claim_slug
from app.use_cases.sharing.share_link_views import build_share_links_view
from app.utilities.sharing.public_slugs import is_reserved_slug

TAKEN_MESSAGE: str = "This address is taken. Try another one."
RESERVED_MESSAGE: str = "This address is reserved. Try another one."


class SetPublicSlugUseCase(UseCaseContract[PublicSlugCommand, ShareLinksView]):
    """
    An owner gives the hosted chat page a new address (`/c/{slug}`).

    The address is taken atomically; one another business has, or ever
    had, is refused (409 `slug_taken`), so a printed QR code never starts
    leading to someone else. The platform's own words and addresses made
    from business ids are refused (422 `slug_reserved`). The business keeps
    its old addresses: they still lead to it, and it can take them back.
    Returns the share links under the new address (untagged).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        public_slug_claim_repo: PublicSlugClaimRepoContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        referral_links: ReferralLinksFacilitatorContract,
    ) -> None:
        self._referral_links: ReferralLinksFacilitatorContract = referral_links
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._public_slug_claim_repo: PublicSlugClaimRepoContract = (
            public_slug_claim_repo
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicSlugCommand) -> ShareLinksView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        slug: BusinessPublicSlug = input_data.request.slug
        if slug != business.public_slug:
            self._take(business, slug)

            def set_slug(stored: BusinessDocument) -> None:
                stored.public_slug = slug

            business = self._business_repo.update(business.id, set_slug)

        return build_share_links_view(
            self._channel_repo,
            self._business_profile_repo,
            self._app_settings,
            business,
            slug,
            None,
            self._referral_links.powered_by_link(business, TABLE_CARD_SOURCE_TAG),
        )

    def _take(self, business: BusinessDocument, slug: BusinessPublicSlug) -> None:
        if is_reserved_slug(slug):
            raise ValidationFailedError(
                RESERVED_MESSAGE,
                reasons=[refusal(PublicSlugRefusalCode.RESERVED, RESERVED_MESSAGE)],
            )

        if not claim_slug(
            self._public_slug_claim_repo,
            business.id,
            slug,
            self._wall_clock.now_unix(),
        ):
            raise ConflictError(
                TAKEN_MESSAGE,
                reasons=[refusal(PublicSlugRefusalCode.TAKEN, TAKEN_MESSAGE)],
            )


def refusal(code: PublicSlugRefusalCode, message: str) -> ErrorReason:
    return ErrorReason(
        code=ErrorReasonCode(code.value),
        message=ErrorReasonMessage(message),
    )
