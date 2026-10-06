"""
What the webhook use cases share: endpoints as the cabinet shows them,
the refusals of an address or a subscription, a new endpoint with its
sealed secret.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.integrations import (
    SUBSCRIBABLE_EVENT_TYPES,
    BusinessEventType,
    WebhookEndpointOrigin,
)
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.integrations.webhook_attempts import WebhookPostResult
from app.schemas.dto.integrations.webhook_views import (
    WebhookDeliveryView,
    WebhookEndpointView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.integrations.constrained_integers import WebhookEndpointCount
from app.schemas.typings.integrations.constrained_strings import (
    WebhookEndpointLabel,
    WebhookSigningSecret,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import ApiKeyId, WebhookEndpointId
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.integrations.integration_secrets import new_signing_secret

# A business keeps at most this many endpoints (a CRM, a sheet, an
# accounting tool and a few Zaps).
MAX_WEBHOOK_ENDPOINTS: WebhookEndpointCount = WebhookEndpointCount(10)
WEBHOOK_ENDPOINT_ENTITY: AuditEntityName = AuditEntityName("webhook_endpoint")
WEBHOOK_DELIVERY_ENTITY: AuditEntityName = AuditEntityName("webhook_delivery")
NOT_PUBLIC_MESSAGE: str = "The webhook address must be a public https address."
TOO_MANY_MESSAGE: str = "This business has as many webhooks as it may have."


def endpoint_view(endpoint: WebhookEndpointDocument) -> WebhookEndpointView:
    return WebhookEndpointView(
        id=endpoint.id,
        url=endpoint.url,
        label=endpoint.label,
        event_types=list(endpoint.event_types),
        status=endpoint.status,
        origin=endpoint.origin,
        secret_hint=endpoint.secret_hint,
        consecutive_failures=endpoint.consecutive_failures,
        last_attempt_at=endpoint.last_attempt_at,
        last_success_at=endpoint.last_success_at,
        disabled_at=endpoint.disabled_at,
        created_at=endpoint.created_at,
    )


def delivery_view(delivery: WebhookDeliveryDocument) -> WebhookDeliveryView:
    return WebhookDeliveryView(
        id=delivery.id,
        endpoint_id=delivery.endpoint_id,
        event_id=delivery.event_id,
        event_type=delivery.event_type,
        status=delivery.status,
        is_test=delivery.is_test,
        attempts=delivery.attempts,
        last_status_code=delivery.last_status_code,
        last_problem=delivery.last_problem,
        last_error=delivery.last_error,
        next_attempt_at=delivery.next_attempt_at,
        last_attempt_at=delivery.last_attempt_at,
        delivered_at=delivery.delivered_at,
        created_at=delivery.created_at,
    )


def require_endpoint(
    endpoint_repo: WebhookEndpointRepoContract,
    business_id: BusinessId,
    endpoint_id: WebhookEndpointId,
) -> WebhookEndpointDocument:
    endpoint = endpoint_repo.get(business_id, endpoint_id)
    if endpoint is None:
        raise NotFoundError("This webhook does not exist (any more).")

    return endpoint


def refuse_address(refusal: WebhookPostResult) -> ValidationFailedError:
    """422 with the reason `not_public` and the problem in its details."""

    problem: str = "not_public" if refusal.problem is None else refusal.problem.value
    return ValidationFailedError(
        NOT_PUBLIC_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode("not_public"),
                message=ErrorReasonMessage(NOT_PUBLIC_MESSAGE),
                details=[ErrorReasonDetail(problem)],
            )
        ],
    )


def subscribed_types(
    event_types: Sequence[BusinessEventType],
) -> list[BusinessEventType]:
    """The asked types in the catalog's order; the test event is refused."""

    if BusinessEventType.WEBHOOK_TEST in event_types:
        raise ValidationFailedError("Nobody subscribes to webhook.test.")

    return [kind for kind in SUBSCRIBABLE_EVENT_TYPES if kind in event_types]


def refuse_when_full(
    endpoint_repo: WebhookEndpointRepoContract, business_id: BusinessId
) -> None:
    if len(endpoint_repo.list_by_business(business_id)) >= int(MAX_WEBHOOK_ENDPOINTS):
        raise ConflictError(
            TOO_MANY_MESSAGE,
            reasons=[
                ErrorReason(
                    code=ErrorReasonCode("webhook_limit_reached"),
                    message=ErrorReasonMessage(TOO_MANY_MESSAGE),
                    details=[ErrorReasonDetail(str(int(MAX_WEBHOOK_ENDPOINTS)))],
                )
            ],
        )


def new_endpoint(
    cipher: SecretCipherAdapterContract,
    business_id: BusinessId,
    url: WebhookTargetUrl,
    label: WebhookEndpointLabel | None,
    event_types: Sequence[BusinessEventType],
    now: Microseconds,
    created_by: UserId | None = None,
    api_key_id: ApiKeyId | None = None,
) -> tuple[WebhookEndpointDocument, WebhookSigningSecret]:
    """A new ACTIVE endpoint with a fresh secret (sealed), and that secret."""

    secret, hint = new_signing_secret()
    endpoint = WebhookEndpointDocument(
        business_id=business_id,
        url=url,
        label=label,
        event_types=subscribed_types(event_types),
        encrypted_secret=cipher.encrypt(ChannelSecret(str(secret))),
        secret_hint=hint,
        origin=WebhookEndpointOrigin.CABINET
        if api_key_id is None
        else WebhookEndpointOrigin.API,
        api_key_id=api_key_id,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    return endpoint, secret
