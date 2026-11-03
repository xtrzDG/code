"""
The Flitt webhook as it runs in production (API-03): the route's use case
verifies and queues, and a worker applies the queued jobs in order. Jobs
wait in a recording queue until the test runs the worker; a job that
fails stays queued for the next run, as the queue retries it.
"""

import json
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.orchestrators.billing.payment_webhook_orchestrator import (
    PaymentWebhookOrchestrator,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.dto.invoicing import BillingEmailsQueued
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.invoicing.constrained_integers import BillingEmailCount
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.billing.payment_webhook.apply_payment_job_use_case import (
    ApplyPaymentJobUseCase,
)
from app.use_cases.billing.payment_webhook.receive_payment_webhook_use_case import (
    ReceivePaymentWebhookUseCase,
)
from tests.billing.billing_settings import sign_flitt_callback
from tests.billing.paid_world import PaidWorld, build_trial


@dataclass(frozen=True)
class QueuedJob:
    job_id: QueuedJobId
    name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None
    serial_key: JobSerialKey | None


@dataclass
class RecordingJobQueue:
    """The jobs queued, oldest first; nothing runs until the test says."""

    jobs: list[QueuedJob] = field(default_factory=list[QueuedJob])

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        del run_at, lane
        job = QueuedJob(QueuedJobId(), job_name, payload, business_id, serial_key)
        self.jobs.append(job)
        return job.job_id


@dataclass
class RecordingDocumentSender:
    receipts: list[PaymentWebhookReceipt] = field(
        default_factory=list[PaymentWebhookReceipt]
    )

    def run(self, input_data: PaymentWebhookReceipt) -> BillingEmailsQueued:
        self.receipts.append(input_data)
        return BillingEmailsQueued(queued=BillingEmailCount(1))


class QueuedWebhookWorld:
    """A business in its trial behind the queued Flitt webhook and a worker."""

    def __init__(self, world: PaidWorld | None = None) -> None:
        self.paid: PaidWorld = world or build_trial()
        testbed = self.paid.testbed
        self.queue = RecordingJobQueue()
        self.documents = RecordingDocumentSender()
        self.receive = ReceivePaymentWebhookUseCase(
            payment_gateway=testbed.payment_gateway,
            payment_order_repo=testbed.payment_order_repo,
            job_queue=self.queue,
            secret_cipher=testbed.secret_cipher,
        )
        self.worker = PaymentWebhookOrchestrator(
            ApplyPaymentJobUseCase(testbed.payments.apply_event, testbed.secret_cipher),
            self.documents,
        )
        self.failures: list[Exception] = []

    def deliver(self, parameters: dict[str, object]) -> PaymentWebhookReceipt:
        """A signed callback as Flitt posts it; Flitt's own record is not changed."""

        return self.receive.run(
            PaymentWebhookDelivery(
                body=PaymentWebhookBody(json.dumps(sign_flitt_callback(parameters))),
                content_type=PaymentWebhookContentType("application/json"),
            )
        )

    def run_jobs(self) -> int:
        """Run every queued job oldest first; a failed one stays queued."""

        done: int = 0
        waiting: list[QueuedJob] = []
        for job in self.queue.jobs:
            try:
                self.worker.execute(
                    QueuedJobInput(
                        job_id=job.job_id,
                        job_name=job.name,
                        payload=job.payload,
                        business_id=job.business_id,
                    )
                )
                done += 1
            except Exception as error:  # noqa: BLE001 - the queue retries it
                self.failures.append(error)
                waiting.append(job)

        self.queue.jobs = waiting
        return done
