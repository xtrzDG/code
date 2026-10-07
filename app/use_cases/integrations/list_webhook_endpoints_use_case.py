from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import SUBSCRIBABLE_EVENT_TYPES
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import (
    WebhookEndpointList,
    WebhookEndpointsQuery,
)
from app.schemas.typings.integrations.constrained_integers import (
    WebhookFailuresBeforeDisable,
)
from app.use_cases.integrations.webhook_records import (
    MAX_WEBHOOK_ENDPOINTS,
    endpoint_view,
)


class ListWebhookEndpointsUseCase(
    UseCaseContract[WebhookEndpointsQuery, WebhookEndpointList]
):
    """
    Settings → Integrations: the business's webhook endpoints, oldest
    first, with the events one may subscribe to and the limits. Owners only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        failures_before_disable: WebhookFailuresBeforeDisable,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._failures_before_disable: WebhookFailuresBeforeDisable = (
            failures_before_disable
        )

    def run(self, input_data: WebhookEndpointsQuery) -> WebhookEndpointList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return WebhookEndpointList(
            items=[
                endpoint_view(endpoint)
                for endpoint in self._endpoint_repo.list_by_business(business.id)
            ],
            event_types=list(SUBSCRIBABLE_EVENT_TYPES),
            max_endpoints=MAX_WEBHOOK_ENDPOINTS,
            failures_before_disable=self._failures_before_disable,
        )
