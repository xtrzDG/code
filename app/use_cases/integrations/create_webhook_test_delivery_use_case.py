from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import BusinessEventType
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.business_events import BusinessEvent, WebhookTestData
from app.schemas.dto.integrations.webhook_attempts import WebhookDeliveryJob
from app.schemas.dto.integrations.webhook_views import WebhookEndpointCommand
from app.schemas.typings.integrations.prefixed_id import BusinessEventId
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.use_cases.integrations.manual_webhook_sends import count_manual_send
from app.use_cases.integrations.webhook_records import require_endpoint
from app.utilities.integrations.public_timestamps import utc_timestamp
from app.utilities.integrations.webhook_schedule import expiry_moment


class CreateWebhookTestDeliveryUseCase(
    UseCaseContract[WebhookEndpointCommand, WebhookDeliveryJob]
):
    """
    "Send test event": a `webhook.test` delivery to one endpoint (it names
    only the endpoint, no customer), tried once right away and kept in the
    log like any other. It does not count towards switching the endpoint
    off. Owners only; with retries, at most MANUAL_SENDS_PER_MINUTE a
    minute per business (429 past them).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        endpoint_repo: WebhookEndpointRepoContract,
        delivery_repo: WebhookDeliveryRepoContract,
        rate_limits: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WebhookEndpointCommand) -> WebhookDeliveryJob:
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
        now: Microseconds = self._wall_clock.now_unix()
        count_manual_send(self._rate_limits, business.id, now)
        envelope = BusinessEvent(
            id=BusinessEventId(),
            type=BusinessEventType.WEBHOOK_TEST,
            created_at=utc_timestamp(now),
            business_id=business.id,
            data=WebhookTestData(endpoint_id=endpoint.id),
        )
        delivery = WebhookDeliveryDocument(
            business_id=business.id,
            endpoint_id=endpoint.id,
            event_id=envelope.id,
            event_type=envelope.type,
            payload=WebhookPayloadJson(envelope.model_dump_json()),
            is_test=True,
            next_attempt_at=now,
            give_up_at=now,
            expires_at=Microseconds(expiry_moment(int(now))),
            created_at=now,
            updated_at=now,
        )
        self._delivery_repo.insert_if_new(delivery)
        return WebhookDeliveryJob(business_id=business.id, delivery_id=delivery.id)
