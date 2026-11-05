"""A business in its trial behind the queued Flitt webhook and its worker."""

import json

from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from tests.billing.billing_settings import sign_flitt_callback
from tests.billing.paid_world import PaidWorld, build_trial
from tests.billing.payment_job_queue import (
    PaymentJobs,
    RecordingDocumentSender,
    RecordingJobQueue,
)


class QueuedWebhookWorld:
    def __init__(self, world: PaidWorld | None = None) -> None:
        self.paid: PaidWorld = world or build_trial()
        self.jobs: PaymentJobs = self.paid.testbed.payment_jobs
        self.queue: RecordingJobQueue = self.jobs.queue
        self.documents: RecordingDocumentSender = self.jobs.documents
        self.failures: list[Exception] = self.jobs.failures

    def deliver(self, parameters: dict[str, object]) -> PaymentWebhookReceipt:
        """A signed callback as Flitt posts it; Flitt's own record is not changed."""

        return self.jobs.receive.run(
            PaymentWebhookDelivery(
                body=PaymentWebhookBody(json.dumps(sign_flitt_callback(parameters))),
                content_type=PaymentWebhookContentType("application/json"),
            )
        )

    def run_jobs(self) -> int:
        """Run every queued job; how many applied (a failed one stays queued)."""

        return len(self.jobs.run())
