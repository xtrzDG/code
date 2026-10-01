from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewQuery,
    BillingOverviewSource,
)


class GetBillingOverviewUseCase(UseCaseContract[BillingOverviewQuery, BillingOverview]):
    """Owner opens the billing page (billing is owner-only, concept section 8)."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ] = assemble_billing_overview

    def run(self, input_data: BillingOverviewQuery) -> BillingOverview:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=business,
                display_language=input_data.display_language,
            )
        )
