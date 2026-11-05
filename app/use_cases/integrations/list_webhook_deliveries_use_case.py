from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import (
    WebhookDeliveriesQuery,
    WebhookDeliveryPage,
)
from app.use_cases.integrations.webhook_records import delivery_view, require_endpoint
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListWebhookDeliveriesUseCase(
    UseCaseContract[WebhookDeliveriesQuery, WebhookDeliveryPage]
):
    """
    An endpoint's delivery log, newest first, one keyset page at a time:
    each event's state, attempts and last answer, without the bodies (no
    customer data). Owners only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        delivery_repo: WebhookDeliveryRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo

    def run(self, input_data: WebhookDeliveriesQuery) -> WebhookDeliveryPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        endpoint = require_endpoint(
            self._endpoint_repo, business.id, input_data.endpoint_id
        )
        fetched: list[WebhookDeliveryDocument] = self._delivery_repo.page_of_endpoint(
            business.id, endpoint.id, read_slice(input_data.page)
        )
        items, next_cursor = finish_page(
            fetched,
            input_data.page,
            lambda delivery: int(delivery.created_at),
            lambda delivery: str(delivery.id),
        )
        return WebhookDeliveryPage(
            items=[delivery_view(delivery) for delivery in items],
            next_cursor=next_cursor,
        )
