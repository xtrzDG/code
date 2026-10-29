from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_cabinet import BillingOverviewSource
from app.schemas.dto.subscription_lifecycle import (
    SubscriptionLifecycleQuery,
    SubscriptionLifecycleView,
)


class GetSubscriptionLifecycleUseCase(
    UseCaseContract[SubscriptionLifecycleQuery, SubscriptionLifecycleView]
):
    """
    GET /v1/businesses/{business_id}/billing/lifecycle: the cancel dialog's
    offers and the pause card (owners only).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        assemble_subscription_lifecycle: UseCaseContract[
            BillingOverviewSource, SubscriptionLifecycleView
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._assemble_subscription_lifecycle: UseCaseContract[
            BillingOverviewSource, SubscriptionLifecycleView
        ] = assemble_subscription_lifecycle

    def run(self, input_data: SubscriptionLifecycleQuery) -> SubscriptionLifecycleView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return self._assemble_subscription_lifecycle.run(
            BillingOverviewSource(
                business=business, display_language=input_data.display_language
            )
        )
