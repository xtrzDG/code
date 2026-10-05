from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.widget_origins import (
    WidgetAllowedOriginsQuery,
    WidgetAllowedOriginsView,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.spend_guard.widget_origin_views import AuthorizeAccess, view_of


class GetWidgetAllowedOriginsUseCase(
    UseCaseContract[WidgetAllowedOriginsQuery, WidgetAllowedOriginsView]
):
    """The websites allowed to show the chat, for every team member."""

    def __init__(
        self,
        authorize_business_access: AuthorizeAccess,
        business_limits_repo: BusinessLimitsRepoContract,
        platform_origins: list[PublicBaseUrl],
    ) -> None:
        self._authorize: AuthorizeAccess = authorize_business_access
        self._limits_repo: BusinessLimitsRepoContract = business_limits_repo
        self._platform_origins: list[PublicBaseUrl] = platform_origins

    def run(self, input_data: WidgetAllowedOriginsQuery) -> WidgetAllowedOriginsView:
        business: BusinessDocument = self._authorize.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return view_of(
            self._limits_repo.get_or_default(business.id), self._platform_origins
        )
