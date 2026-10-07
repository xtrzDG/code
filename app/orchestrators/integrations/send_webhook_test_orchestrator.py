from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookAttempt,
    WebhookDeliveryJob,
)
from app.schemas.dto.integrations.webhook_views import (
    WebhookDeliveryView,
    WebhookEndpointCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.integrations.webhook_records import delivery_view


class SendWebhookTestOrchestrator(
    OrchestratorContract[WebhookEndpointCommand, WebhookDeliveryView]
):
    """
    "Send test event": a test delivery made for the endpoint, tried at
    once with the job's own attempt and recording, and its outcome shown
    to the owner right away (the status code, or why it failed).
    """

    def __init__(
        self,
        create_test_delivery: UseCaseContract[
            WebhookEndpointCommand, WebhookDeliveryJob
        ],
        attempt_delivery: UseCaseContract[WebhookDeliveryJob, WebhookAttempt | None],
        record_attempt: UseCaseContract[WebhookAttempt, WebhookDeliveryDocument | None],
    ) -> None:
        self._create_test_delivery: UseCaseContract[
            WebhookEndpointCommand, WebhookDeliveryJob
        ] = create_test_delivery
        self._attempt_delivery: UseCaseContract[
            WebhookDeliveryJob, WebhookAttempt | None
        ] = attempt_delivery
        self._record_attempt: UseCaseContract[
            WebhookAttempt, WebhookDeliveryDocument | None
        ] = record_attempt

    def execute(self, input_data: WebhookEndpointCommand) -> WebhookDeliveryView:
        attempt = self._attempt_delivery.run(self._create_test_delivery.run(input_data))
        recorded = None if attempt is None else self._record_attempt.run(attempt)
        if recorded is None:
            raise ConflictError("The test event could not be sent; try again.")

        return delivery_view(recorded)
