from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_views import ValueSettingsQuery, ValueSettingsView
from app.use_cases.insights.value.value_estimates import (
    EstimateCatalogs,
    estimate_business_value,
)
from app.use_cases.insights.value.value_settings_views import (
    build_value_settings_view,
)


class GetValueSettingsUseCase(UseCaseContract[ValueSettingsQuery, ValueSettingsView]):
    """
    The owner's average check, the niche's typical check in the business
    currency, and what earns money in the estimate (owners).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        catalogs: EstimateCatalogs,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._catalogs: EstimateCatalogs = catalogs

    def run(self, input_data: ValueSettingsQuery) -> ValueSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return build_value_settings_view(
            business,
            self._catalogs.value_settings_repo.get_by_business(business.id),
            estimate_business_value(self._catalogs, business),
        )
