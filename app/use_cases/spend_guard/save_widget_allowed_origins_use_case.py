from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.widget_origins import (
    SaveWidgetAllowedOriginsCommand,
    WidgetAllowedOriginsView,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.spend_guard.widget_origin_views import AuthorizeAccess, view_of
from app.utilities.spend.widget_origins import normalize_site_address, unique_sites


class SaveWidgetAllowedOriginsUseCase(
    UseCaseContract[SaveWidgetAllowedOriginsCommand, WidgetAllowedOriginsView]
):
    """
    The owner sets the websites allowed to show the chat: each address as
    its origin ("cafe-batumi.ge/menu" -> "https://cafe-batumi.ge"), one per
    site, in the owner's order. An empty list lets any website show it.

    Raises:
        ValidationFailedError: an address is not a website.
    """

    def __init__(
        self,
        authorize_business_access: AuthorizeAccess,
        business_limits_repo: BusinessLimitsRepoContract,
        platform_origins: list[PublicBaseUrl],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize: AuthorizeAccess = authorize_business_access
        self._limits_repo: BusinessLimitsRepoContract = business_limits_repo
        self._platform_origins: list[PublicBaseUrl] = platform_origins
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: SaveWidgetAllowedOriginsCommand
    ) -> WidgetAllowedOriginsView:
        business: BusinessDocument = self._authorize.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        origins: list[PublicBaseUrl] = unique_sites(
            normalize_site_address(address) for address in input_data.request.origins
        )
        limits: BusinessLimitsDocument = self._limits_repo.get_or_default(business.id)
        limits.widget_allowed_origins = origins
        limits.updated_at = self._wall_clock.now_unix()
        self._limits_repo.save(limits)
        return view_of(limits, self._platform_origins)
