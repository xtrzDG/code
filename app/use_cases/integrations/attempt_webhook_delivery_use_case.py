from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import WebhookPosterContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import (
    WebhookDeliveryProblem,
    WebhookDeliveryStatus,
    WebhookEndpointStatus,
)
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookAttempt,
    WebhookDeliveryJob,
    WebhookPostRequest,
    WebhookPostResult,
)
from app.schemas.typings.integrations.constrained_strings import (
    WebhookErrorText,
    WebhookSigningSecret,
)
from app.utilities.integrations.webhook_signatures import sign_webhook_body

MICROSECONDS_PER_SECOND: int = 1_000_000
ENDPOINT_OFF: WebhookPostResult = WebhookPostResult(
    problem=WebhookDeliveryProblem.ENDPOINT_OFF,
    error=WebhookErrorText("The webhook was paused, switched off or removed."),
)


class AttemptWebhookDeliveryUseCase(
    UseCaseContract[WebhookDeliveryJob, WebhookAttempt | None]
):
    """
    One attempt of a delivery: the stored body, signed now with the
    endpoint's secret (`Workshop-Signature: t=…,v1=…`), posted through the
    SSRF guard. Nothing is sent when the delivery is no longer waiting or
    its attempt is not due yet (a job of an earlier schedule), and nothing
    but the refusal is recorded when its endpoint was paused, switched off
    or removed meanwhile (a test event still goes to a paused one).
    """

    def __init__(
        self,
        delivery_repo: WebhookDeliveryRepoContract,
        endpoint_repo: WebhookEndpointRepoContract,
        cipher: SecretCipherAdapterContract,
        poster: WebhookPosterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._cipher: SecretCipherAdapterContract = cipher
        self._poster: WebhookPosterContract = poster
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WebhookDeliveryJob) -> WebhookAttempt | None:
        delivery = self._delivery_repo.get(
            input_data.business_id, input_data.delivery_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        if delivery is None or not is_due(delivery, now):
            return None

        endpoint = self._endpoint_repo.get(delivery.business_id, delivery.endpoint_id)
        if endpoint is None or not may_receive(endpoint, delivery):
            return WebhookAttempt(
                delivery=delivery, result=ENDPOINT_OFF, attempted_at=now
            )

        secret = WebhookSigningSecret(
            str(self._cipher.decrypt(endpoint.encrypted_secret))
        )
        result: WebhookPostResult = self._poster.post(
            WebhookPostRequest(
                url=endpoint.url,
                body=delivery.payload,
                signature=sign_webhook_body(
                    secret, int(now) // MICROSECONDS_PER_SECOND, delivery.payload
                ),
                event_id=delivery.event_id,
                event_type=delivery.event_type,
                delivery_id=delivery.id,
            )
        )
        return WebhookAttempt(
            delivery=delivery, result=result, attempted_at=self._wall_clock.now_unix()
        )


def is_due(delivery: WebhookDeliveryDocument, now: Microseconds) -> bool:
    """Waiting, and its attempt is now (a job of an older schedule is not)."""

    return delivery.status is WebhookDeliveryStatus.PENDING and (
        delivery.next_attempt_at is None or int(delivery.next_attempt_at) <= int(now)
    )


def may_receive(
    endpoint: WebhookEndpointDocument, delivery: WebhookDeliveryDocument
) -> bool:
    if endpoint.status is WebhookEndpointStatus.ACTIVE:
        return True

    return delivery.is_test and endpoint.status is WebhookEndpointStatus.PAUSED
