"""An endpoint follows its deliveries: failures in a row, switched off."""

from typed_time_provider import Microseconds

from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.schemas.constants.integrations import (
    WebhookDeliveryProblem,
    WebhookEndpointOrigin,
    WebhookEndpointStatus,
)
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.integrations.webhook_attempts import WebhookAttempt
from app.schemas.typings.integrations.constrained_integers import (
    WebhookFailureCount,
    WebhookFailuresBeforeDisable,
)


def record_endpoint_outcome(
    endpoint_repo: WebhookEndpointRepoContract,
    delivery: WebhookDeliveryDocument,
    attempt: WebhookAttempt,
    failures_before_disable: WebhookFailuresBeforeDisable,
) -> WebhookEndpointDocument | None:
    """
    A real event's attempt counts on its endpoint (a test event, or one
    refused because the endpoint was off, does not). A receiver's 410 Gone
    removes an endpoint a public API client subscribed (its REST hook was
    unsubscribed) and switches off one the owner added. Returns the
    endpoint when this attempt switched it off (only one attempt can: the
    switch-off happens while the stored endpoint is ACTIVE), else None.
    """

    problem = attempt.result.problem
    if delivery.is_test or problem is WebhookDeliveryProblem.ENDPOINT_OFF:
        return None

    endpoint = endpoint_repo.get(delivery.business_id, delivery.endpoint_id)
    if endpoint is None:
        return None

    if (
        problem is WebhookDeliveryProblem.GONE
        and endpoint.origin is WebhookEndpointOrigin.API
    ):
        endpoint_repo.delete(delivery.business_id, endpoint.id)
        return None

    now: Microseconds = attempt.attempted_at
    switched_off: list[bool] = [False]

    def follow(current: WebhookEndpointDocument) -> WebhookEndpointDocument:
        updated = followed(current, problem, now, failures_before_disable)
        switched_off[0] = (
            current.status is WebhookEndpointStatus.ACTIVE
            and updated.status is WebhookEndpointStatus.DISABLED
        )
        return updated

    stored = endpoint_repo.update(delivery.business_id, endpoint.id, follow)
    return stored if stored is not None and switched_off[0] else None


def followed(
    current: WebhookEndpointDocument,
    problem: WebhookDeliveryProblem | None,
    now: Microseconds,
    failures_before_disable: WebhookFailuresBeforeDisable,
) -> WebhookEndpointDocument:
    if problem is None:
        return current.model_copy(
            update={
                "consecutive_failures": WebhookFailureCount(0),
                "last_attempt_at": now,
                "last_success_at": now,
                "updated_at": now,
            }
        )

    failures = WebhookFailureCount(int(current.consecutive_failures) + 1)
    switch_off: bool = current.status is WebhookEndpointStatus.ACTIVE and (
        problem is WebhookDeliveryProblem.GONE
        or int(failures) >= int(failures_before_disable)
    )
    return current.model_copy(
        update={
            "consecutive_failures": failures,
            "last_attempt_at": now,
            "status": WebhookEndpointStatus.DISABLED if switch_off else current.status,
            "disabled_at": now if switch_off else current.disabled_at,
            "updated_at": now,
        }
    )
