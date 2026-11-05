"""One attempt of a webhook delivery: the request, and what came of it."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.integrations import (
    BusinessEventType,
    WebhookDeliveryProblem,
)
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.constrained_strings import (
    WebhookErrorText,
    WebhookSignature,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import (
    BusinessEventId,
    WebhookDeliveryId,
)
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.schemas.typings.observability.constrained_integers import HttpStatusCode


class WebhookPostRequest(ImmutableDTO):
    """
    A signed webhook request: where, the exact body, its signature and
    the ids a receiver logs or drops repeats by (sent as headers).
    """

    url: WebhookTargetUrl
    body: WebhookPayloadJson
    signature: WebhookSignature
    event_id: BusinessEventId
    event_type: BusinessEventType
    delivery_id: WebhookDeliveryId


class WebhookPostResult(ImmutableDTO):
    """
    What the receiver did: answered with `status_code` (2xx is delivered),
    or could not be reached (`problem`, `error`).
    """

    status_code: HttpStatusCode | None = None
    problem: WebhookDeliveryProblem | None = None
    error: WebhookErrorText | None = None


class WebhookDeliveryJob(ImmutableDTO):
    """The payload of a `deliver_webhook` job: which delivery to try."""

    business_id: BusinessId
    delivery_id: WebhookDeliveryId


class WebhookAttempt(ImmutableDTO):
    """
    An attempt made (or refused before sending: the endpoint is off) and
    when, to be recorded on the delivery and its endpoint.
    """

    delivery: WebhookDeliveryDocument
    result: WebhookPostResult
    attempted_at: Microseconds
