"""
The payment webhooks as production runs them (API-03): the route's use case
verifies and queues into a recording queue, and `run` is the worker that
applies the queued jobs oldest first. A job that fails stays queued for the
next run, as the queue retries it.
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.billing.payment_webhook_orchestrator import (
    PaymentWebhookOrchestrator,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.dto.invoicing import BillingEmailsQueued
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.payments import PaymentWebhookReceipt, VerifiedPaymentEvent
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


class RecordingApply(UseCaseContract[QueuedJobInput, PaymentWebhookReceipt]):
    """The job's use case, keeping what each run applied."""

    def __init__(self, inner: ApplyPaymentJobUseCase) -> None:
        self._inner: ApplyPaymentJobUseCase = inner
        self.receipts: list[PaymentWebhookReceipt] = []

    def run(self, input_data: QueuedJobInput) -> PaymentWebhookReceipt:
        receipt: PaymentWebhookReceipt = self._inner.run(input_data)
        self.receipts.append(receipt)
        return receipt


class PaymentJobs:
    """The webhook's use case, its queue and the worker of that queue."""

    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        payment_order_repo: PaymentOrderRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        apply_event: UseCaseContract[VerifiedPaymentEvent, PaymentWebhookReceipt],
    ) -> None:
        self.queue = RecordingJobQueue()
        self.documents = RecordingDocumentSender()
        self.receive = ReceivePaymentWebhookUseCase(
            payment_gateway=payment_gateway,
            payment_order_repo=payment_order_repo,
            job_queue=self.queue,
            secret_cipher=secret_cipher,
        )
        self._applied = RecordingApply(
            ApplyPaymentJobUseCase(apply_event, secret_cipher)
        )
        self.worker = PaymentWebhookOrchestrator(self._applied, self.documents)
        self.failures: list[Exception] = []

    def run(self) -> list[PaymentWebhookReceipt]:
        """Run every queued job oldest first: what each applied job did."""

        applied_before: int = len(self._applied.receipts)
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
            except Exception as error:  # noqa: BLE001 - the queue retries it
                self.failures.append(error)
                waiting.append(job)

        self.queue.jobs = waiting
        return self._applied.receipts[applied_before:]
