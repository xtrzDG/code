from typed_time_provider import Microseconds, WallClock

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
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.sharing import ShareLinksQuery, ShareLinksView
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.use_cases.sharing.public_slug_claims import ensure_public_slug
from app.use_cases.sharing.share_link_views import build_share_links_view


class GetShareLinksUseCase(UseCaseContract[ShareLinksQuery, ShareLinksView]):
    """
    The links an owner or staff member shares so customers can start a
    conversation (cabinet: Channels, "Share"): the hosted chat page
    (`{CABINET_BASE_URL}/c/{slug}`) and a link per channel that is switched
    on, tagged with where they will be put (`source`).

    A business gets its public address the first time anyone opens this:
    one suggested from its name, taken atomically (an owner can change it
    later). Channels connected before the platform learned their public
    address are listed with a gap: reconnecting them once fills it.
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
    ) -> None:
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

    def run(self, input_data: ShareLinksQuery) -> ShareLinksView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        slug: BusinessPublicSlug
        business, slug = ensure_public_slug(
            self._business_repo,
            self._public_slug_claim_repo,
            business,
            self._wall_clock.now_unix(),
        )
        return build_share_links_view(
            self._channel_repo,
            self._business_profile_repo,
            self._app_settings,
            business,
            slug,
            input_data.source,
        )
