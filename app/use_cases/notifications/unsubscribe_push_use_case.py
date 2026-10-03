from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import PushDeviceCommand
from app.use_cases.notifications.notification_views import require_own_device


class UnsubscribePushUseCase(UseCaseContract[PushDeviceCommand, None]):
    """A member turns notifications off on one of their own devices."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        push_subscription_repo: PushSubscriptionRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )

    def run(self, input_data: PushDeviceCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        device: PushSubscriptionDocument = require_own_device(
            self._push_subscription_repo, business, input_data
        )
        self._push_subscription_repo.delete(business.id, device.id)
