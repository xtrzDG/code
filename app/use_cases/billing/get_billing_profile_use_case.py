from app.contracts.invoicing import (
    BillingProfileRepoContract,
    TaxPolicyRegistryContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_profiles import BillingProfileQuery, BillingProfileView
from app.use_cases.billing.billing_profile_views import view_billing_profile


class GetBillingProfileUseCase(
    UseCaseContract[BillingProfileQuery, BillingProfileView]
):
    """
    An owner opens the billing details (owner-only, like all of billing):
    what the next invoices will say about the business, and their VAT.
    Before the owner saved any, the business's name and country.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        billing_profile_repo: BillingProfileRepoContract,
        tax_policy_registry: TaxPolicyRegistryContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._billing_profile_repo: BillingProfileRepoContract = billing_profile_repo
        self._tax_policy_registry: TaxPolicyRegistryContract = tax_policy_registry

    def run(self, input_data: BillingProfileQuery) -> BillingProfileView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return view_billing_profile(
            business,
            self._billing_profile_repo.get_by_business(business.id),
            self._tax_policy_registry,
        )
