"""
Outbound webhooks (migration 1181): the addresses a business has events
sent to, and every event's delivery to each of them with its attempts.
"""

from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.integrations import (
    BusinessEventType,
    WebhookDeliveryProblem,
    WebhookDeliveryStatus,
    WebhookEndpointOrigin,
    WebhookEndpointStatus,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.integrations.booleans import IsTestDelivery
from app.schemas.typings.integrations.constrained_integers import (
    WebhookAttemptCount,
    WebhookFailureCount,
)
from app.schemas.typings.integrations.constrained_strings import (
    WebhookEndpointLabel,
    WebhookErrorText,
    WebhookSecretHint,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import (
    ApiKeyId,
    BusinessEventId,
    WebhookDeliveryId,
    WebhookEndpointId,
)
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.schemas.typings.observability.constrained_integers import HttpStatusCode
from app.schemas.typings.users.prefixed_id import UserId


class WebhookEndpointDocument(BaseDocument):
    """
    One address a business has its events sent to (a business collection).

    `event_types` are the events it subscribed to. Every request is signed
    with its secret, kept sealed with the platform key ring
    (`encrypted_secret`; `secret_hint` is its last four characters). Only
    an ACTIVE endpoint gets new events. `consecutive_failures` counts the
    failed attempts since the last success; past the limit
    (WEBHOOK_DISABLE_AFTER_FAILURES) the endpoint is DISABLED, as it is when
    the receiver answers 410 Gone. An endpoint a public API client
    subscribed (`origin` API) names the key it came with (`api_key_id`).
    """

    id: WebhookEndpointId = Field(default_factory=WebhookEndpointId)
    business_id: BusinessId
    url: WebhookTargetUrl
    label: WebhookEndpointLabel | None = None
    event_types: list[BusinessEventType] = Field(min_length=1)
    encrypted_secret: EncryptedChannelSecret
    secret_hint: WebhookSecretHint
    status: WebhookEndpointStatus = WebhookEndpointStatus.ACTIVE
    origin: WebhookEndpointOrigin = WebhookEndpointOrigin.CABINET
    api_key_id: ApiKeyId | None = None
    consecutive_failures: WebhookFailureCount = WebhookFailureCount(0)
    last_attempt_at: Microseconds | None = None
    last_success_at: Microseconds | None = None
    disabled_at: Microseconds | None = None
    created_by: UserId | None = None


class WebhookDeliveryDocument(BaseDocument):
    """
    One event's delivery to one endpoint (a business collection): the
    exact body sent on every attempt (`payload`, the event as it was when
    it happened), and how the attempts went. A PENDING delivery has its
    next attempt at `next_attempt_at` (a queued job); attempts stop at
    `give_up_at`, 24 hours after the event. The delivery log keeps it
    until `expires_at` (30 days), when the daily purge deletes it.
    """

    id: WebhookDeliveryId = Field(default_factory=WebhookDeliveryId)
    business_id: BusinessId
    endpoint_id: WebhookEndpointId
    event_id: BusinessEventId
    event_type: BusinessEventType
    payload: WebhookPayloadJson
    is_test: IsTestDelivery = False
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    attempts: WebhookAttemptCount = WebhookAttemptCount(0)
    next_attempt_at: Microseconds | None = None
    last_attempt_at: Microseconds | None = None
    last_status_code: HttpStatusCode | None = None
    last_problem: WebhookDeliveryProblem | None = None
    last_error: WebhookErrorText | None = None
    delivered_at: Microseconds | None = None
    give_up_at: Microseconds
    expires_at: Microseconds
