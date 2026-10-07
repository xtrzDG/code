from app.contracts.repositories.customer_repositories import (
    CustomerSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_settings import (
    CustomerSettingsQuery,
    CustomerSettingsView,
)


class GetCustomerSettingsUseCase(
    UseCaseContract[CustomerSettingsQuery, CustomerSettingsView]
):
    """
    Customers' settings for the team: whether staff see phone numbers and
    the business's tags (offered when tagging). Owners and staff; the
    defaults without a stored document.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        customer_settings_repo: CustomerSettingsRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._customer_settings_repo: CustomerSettingsRepoContract = (
            customer_settings_repo
        )

    def run(self, input_data: CustomerSettingsQuery) -> CustomerSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        settings: CustomerSettingsDocument | None = (
            self._customer_settings_repo.get_by_business(business.id)
        )
        return settings_view(settings)


def settings_view(settings: CustomerSettingsDocument | None) -> CustomerSettingsView:
    if settings is None:
        return CustomerSettingsView()

    return CustomerSettingsView(
        staff_sees_phone_numbers=settings.staff_sees_phone_numbers,
        known_tags=list(settings.known_tags),
    )
