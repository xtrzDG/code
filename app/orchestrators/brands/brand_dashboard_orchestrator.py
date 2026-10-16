from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.dto.brands.brand_commands import BrandQuery
from app.schemas.dto.brands.brand_dashboard import (
    BrandDashboard,
    BrandDashboardQuery,
    BrandLocationDashboard,
)
from app.schemas.dto.brands.brand_views import BrandLocationView, BrandView
from app.schemas.dto.inbox.inbox_attention import (
    InboxAttentionCounts,
    InboxAttentionQuery,
)
from app.schemas.dto.value.customer_sources import (
    CustomerSourcesQuery,
    CustomerSourcesView,
)
from app.schemas.dto.value.value_model import ValueModel
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError


class BrandDashboardOrchestrator(
    OrchestratorContract[BrandDashboardQuery, BrandDashboard]
):
    """
    GET /v1/brands/{brand_id}/dashboard: the brand's locations side by
    side. The brand is read for the member (others: 404) and lists the
    locations they reach; each location is then read inside its own
    storage scope, through the location's own value, sources and inbox use
    cases, which check the member's access to it again. A brand request
    never runs platform-wide, and row-level security keeps every read in
    the location it names. Sources are a brand owner's (owners only, as
    in the location's cabinet). A location that asks for a two-factor
    sign-in the session lacks is shown locked; one that left the brand
    meanwhile is left out.
    """

    def __init__(
        self,
        get_brand: UseCaseContract[BrandQuery, BrandView],
        get_value: UseCaseContract[BusinessValueQuery, ValueModel],
        get_sources: UseCaseContract[CustomerSourcesQuery, CustomerSourcesView],
        count_inbox: UseCaseContract[InboxAttentionQuery, InboxAttentionCounts],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._get_brand: UseCaseContract[BrandQuery, BrandView] = get_brand
        self._get_value: UseCaseContract[BusinessValueQuery, ValueModel] = get_value
        self._get_sources: UseCaseContract[
            CustomerSourcesQuery, CustomerSourcesView
        ] = get_sources
        self._count_inbox: UseCaseContract[
            InboxAttentionQuery, InboxAttentionCounts
        ] = count_inbox
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: BrandDashboardQuery) -> BrandDashboard:
        brand: BrandView = self._get_brand.run(
            BrandQuery(user_id=input_data.user_id, brand_id=input_data.brand_id)
        )
        is_owner: bool = brand.viewer_role is BrandMemberRole.BRAND_OWNER
        locations: list[BrandLocationDashboard] = []
        for location in brand.locations:
            try:
                with self._storage_scope.scoped_to_business(location.business_id):
                    locations.append(
                        self._describe(location, input_data, include_sources=is_owner)
                    )
            except NotFoundError:
                continue
            except AccessDeniedError:
                locations.append(
                    BrandLocationDashboard(location=location, is_locked=True)
                )

        return BrandDashboard(
            brand_id=brand.id,
            name=brand.name,
            viewer_role=brand.viewer_role,
            locations=locations,
        )

    def _describe(
        self,
        location: BrandLocationView,
        query: BrandDashboardQuery,
        include_sources: bool,
    ) -> BrandLocationDashboard:
        value: ValueModel = self._get_value.run(
            BusinessValueQuery(
                user_id=query.user_id,
                business_id=location.business_id,
                period=query.period,
                date_from=query.date_from,
                date_to=query.date_to,
            )
        )
        sources: CustomerSourcesView | None = (
            self._get_sources.run(
                CustomerSourcesQuery(
                    user_id=query.user_id,
                    business_id=location.business_id,
                    period=query.period,
                    date_from=query.date_from,
                    date_to=query.date_to,
                )
            )
            if include_sources
            else None
        )
        return BrandLocationDashboard(
            location=location,
            value=value,
            sources=sources,
            inbox=self._count_inbox.run(
                InboxAttentionQuery(
                    user_id=query.user_id, business_id=location.business_id
                )
            ),
        )
