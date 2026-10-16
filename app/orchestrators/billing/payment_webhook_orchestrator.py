import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.invoicing import BillingEmailsQueued
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt

logger: logging.Logger = logging.getLogger(__name__)

# Outcomes after which invoices may have been paid just now.
PAYING_OUTCOMES: frozenset[PaymentWebhookOutcome] = frozenset(
    {PaymentWebhookOutcome.APPLIED, PaymentWebhookOutcome.REFUND_DUE}
)


class PaymentWebhookOrchestrator(
    OrchestratorContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
):
    """
    A payment provider notification (POST /v1/payments/flitt/webhook):

    1. Apply it (`ProcessPaymentWebhookUseCase`): invoices paid or failed,
       the subscription moved, owners told about a decline.
    2. When it may have paid invoices, e-mail each one with its receipt to
       the billing contact (`SendPaymentDocumentsUseCase`). The payment is
       already recorded then, so a failure here is logged and never makes
       the provider send the notification again; the cabinet keeps the
       PDFs for download either way.
    """

    def __init__(
        self,
        process_payment_webhook: UseCaseContract[
            PaymentWebhookDelivery, PaymentWebhookReceipt
        ],
        send_payment_documents: UseCaseContract[
            PaymentWebhookReceipt, BillingEmailsQueued
        ],
    ) -> None:
        self._process_payment_webhook: UseCaseContract[
            PaymentWebhookDelivery, PaymentWebhookReceipt
        ] = process_payment_webhook
        self._send_payment_documents: UseCaseContract[
            PaymentWebhookReceipt, BillingEmailsQueued
        ] = send_payment_documents

    def execute(self, input_data: PaymentWebhookDelivery) -> PaymentWebhookReceipt:
        receipt: PaymentWebhookReceipt = self._process_payment_webhook.run(input_data)
        if receipt.outcome not in PAYING_OUTCOMES:
            return receipt

        try:
            self._send_payment_documents.run(receipt)
        except Exception:
            logger.exception("Invoice e-mails after a payment could not be queued.")

        return receipt
