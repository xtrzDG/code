"""Settings → Integrations: webhook endpoints and their delivery log."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.integrations import (
    BusinessEventType,
    WebhookDeliveryProblem,
    WebhookDeliveryStatus,
    WebhookEndpointOrigin,
    WebhookEndpointStatus,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.integrations.booleans import IsTestDelivery
from app.schemas.typings.integrations.constrained_integers import (
    WebhookAttemptCount,
    WebhookEndpointCount,
    WebhookFailureCount,
    WebhookFailuresBeforeDisable,
)
from app.schemas.typings.integrations.constrained_strings import (
    WebhookEndpointLabel,
    WebhookErrorText,
    WebhookSecretHint,
    WebhookSigningSecret,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import (
    BusinessEventId,
    WebhookDeliveryId,
    WebhookEndpointId,
)
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.schemas.typings.observability.constrained_integers import HttpStatusCode
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class WebhookEndpointView(ImmutableDTO):
    """
    One endpoint as the cabinet shows it: where, what it subscribed to,
    its state and how the latest attempts went. The secret shows only its
    last four characters.
    """

    id: WebhookEndpointId
    url: WebhookTargetUrl
    label: WebhookEndpointLabel | None = None
    event_types: list[BusinessEventType]
    status: WebhookEndpointStatus
    origin: WebhookEndpointOrigin
    secret_hint: WebhookSecretHint
    consecutive_failures: WebhookFailureCount
    last_attempt_at: Microseconds | None = None
    last_success_at: Microseconds | None = None
    disabled_at: Microseconds | None = None
    created_at: Microseconds


class WebhookEndpointList(ImmutableDTO):
    """
    The business's endpoints, the events one may subscribe to, how many
    endpoints a business may have, and after how many failed attempts in
    a row an endpoint is switched off.
    """

    items: list[WebhookEndpointView] = Field(default_factory=list[WebhookEndpointView])
    event_types: list[BusinessEventType]
    max_endpoints: WebhookEndpointCount
    failures_before_disable: WebhookFailuresBeforeDisable


class WebhookEndpointRequest(ImmutableDTO):
    """A new endpoint: its https address, a note, what it subscribes to."""

    url: WebhookTargetUrl
    label: WebhookEndpointLabel | None = None
    event_types: list[BusinessEventType] = Field(min_length=1)


class WebhookEndpointChange(ImmutableDTO):
    """
    A change of an endpoint; omitted fields stay. `status` ACTIVE switches
    it on (also after it was switched off for failures: the count starts
    again), PAUSED stops new events.
    """

    url: WebhookTargetUrl | None = None
    label: WebhookEndpointLabel | None = None
    event_types: list[BusinessEventType] | None = Field(default=None, min_length=1)
    status: WebhookEndpointStatus | None = None


class WebhookEndpointsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class CreateWebhookEndpointCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: WebhookEndpointRequest
    client_ip_address: ClientIpAddress | None = None


class UpdateWebhookEndpointCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    endpoint_id: WebhookEndpointId
    change: WebhookEndpointChange
    client_ip_address: ClientIpAddress | None = None


class WebhookEndpointCommand(ImmutableDTO):
    """An action on one endpoint: a new secret, removal, a test event."""

    user_id: UserId
    business_id: BusinessId
    endpoint_id: WebhookEndpointId
    client_ip_address: ClientIpAddress | None = None


class CreatedWebhookEndpoint(ImmutableDTO):
    """
    An endpoint with its signing secret, shown this once (when it was made
    or given a new secret): the receiver checks signatures with it.
    """

    endpoint: WebhookEndpointView
    signing_secret: WebhookSigningSecret


class WebhookDeliveryView(ImmutableDTO):
    """One event's delivery in the log: its state and the last attempt."""

    id: WebhookDeliveryId
    endpoint_id: WebhookEndpointId
    event_id: BusinessEventId
    event_type: BusinessEventType
    status: WebhookDeliveryStatus
    is_test: IsTestDelivery = False
    attempts: WebhookAttemptCount
    last_status_code: HttpStatusCode | None = None
    last_problem: WebhookDeliveryProblem | None = None
    last_error: WebhookErrorText | None = None
    next_attempt_at: Microseconds | None = None
    last_attempt_at: Microseconds | None = None
    delivered_at: Microseconds | None = None
    created_at: Microseconds


class WebhookDeliveryPage(ImmutableDTO):
    items: list[WebhookDeliveryView] = Field(default_factory=list[WebhookDeliveryView])
    next_cursor: PageCursor | None = None


class WebhookDeliveriesQuery(ImmutableDTO):
    """An endpoint's delivery log, newest first."""

    user_id: UserId
    business_id: BusinessId
    endpoint_id: WebhookEndpointId
    page: PageRequest


class WebhookDeliveryCommand(ImmutableDTO):
    """One delivery: read with its body (audited), or sent again."""

    user_id: UserId
    business_id: BusinessId
    delivery_id: WebhookDeliveryId
    client_ip_address: ClientIpAddress | None = None


class WebhookDeliveryDetail(ImmutableDTO):
    """A delivery with the exact JSON body it sends (customer data in it)."""

    delivery: WebhookDeliveryView
    payload: WebhookPayloadJson
