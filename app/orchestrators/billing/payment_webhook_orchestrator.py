import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.invoicing import BillingEmailsQueued
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount

logger: logging.Logger = logging.getLogger(__name__)

# Outcomes after which invoices may have been paid just now.
PAYING_OUTCOMES: frozenset[PaymentWebhookOutcome] = frozenset(
    {PaymentWebhookOutcome.APPLIED, PaymentWebhookOutcome.REFUND_DUE}
)


class PaymentWebhookOrchestrator(OrchestratorContract[QueuedJobInput, JobReport]):
    """
    A payment provider notification the webhook verified and queued (the
    job `apply_payment_notification`, API-03):

    1. Apply it (`ApplyPaymentJobUseCase`): invoices paid
       or failed, the subscription moved, owners told about a decline. A
       failure here raises, and the queue runs the job again.
    2. When it may have paid invoices, e-mail each one with its receipt to
       the billing contact (`SendPaymentDocumentsUseCase`). The payment is
       already recorded then, so a failure here is logged and never runs
       the job again; the cabinet keeps the PDFs for download either way.
    """

    def __init__(
        self,
        apply_payment_notification: UseCaseContract[
            QueuedJobInput, PaymentWebhookReceipt
        ],
        send_payment_documents: UseCaseContract[
            PaymentWebhookReceipt, BillingEmailsQueued
        ],
    ) -> None:
        self._apply_payment_notification: UseCaseContract[
            QueuedJobInput, PaymentWebhookReceipt
        ] = apply_payment_notification
        self._send_payment_documents: UseCaseContract[
            PaymentWebhookReceipt, BillingEmailsQueued
        ] = send_payment_documents

    def execute(self, input_data: QueuedJobInput) -> JobReport:
        receipt: PaymentWebhookReceipt = self._apply_payment_notification.run(
            input_data
        )
        if receipt.outcome not in PAYING_OUTCOMES:
            return JobReport(processed_count=ProcessedItemCount(1))

        try:
            self._send_payment_documents.run(receipt)
        except Exception:
            logger.exception("Invoice e-mails after a payment could not be queued.")

        return JobReport(processed_count=ProcessedItemCount(1))
