from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookAttempt,
    WebhookDeliveryJob,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.utilities.integrations.webhook_jobs import decode_webhook_job


class DeliverWebhookOrchestrator(OrchestratorContract[QueuedJobInput, JobReport]):
    """
    The `deliver_webhook` job: one attempt of one delivery (signed, posted
    through the SSRF guard), then its outcome recorded with the next
    attempt queued or the delivery finished, and its endpoint following.
    """

    def __init__(
        self,
        attempt_delivery: UseCaseContract[WebhookDeliveryJob, WebhookAttempt | None],
        record_attempt: UseCaseContract[WebhookAttempt, WebhookDeliveryDocument | None],
    ) -> None:
        self._attempt_delivery: UseCaseContract[
            WebhookDeliveryJob, WebhookAttempt | None
        ] = attempt_delivery
        self._record_attempt: UseCaseContract[
            WebhookAttempt, WebhookDeliveryDocument | None
        ] = record_attempt

    def execute(self, input_data: QueuedJobInput) -> JobReport:
        attempt = self._attempt_delivery.run(decode_webhook_job(input_data.payload))
        if attempt is None:
            return JobReport()

        recorded = self._record_attempt.run(attempt)
        return JobReport(
            processed_count=ProcessedItemCount(0 if recorded is None else 1)
        )
