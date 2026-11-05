from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.payments import PaymentWebhookReceipt, VerifiedPaymentEvent
from app.use_cases.billing.payment_webhook.payment_notification_jobs import (
    decode_payment_notification,
)


class ApplyPaymentJobUseCase(UseCaseContract[QueuedJobInput, PaymentWebhookReceipt]):
    """
    Queued job `apply_payment_notification` (API-03): the verified event a
    payment webhook queued, opened with the platform's key ring (only the
    webhook seals one, after checking the provider's signature) and applied
    (`ApplyPaymentEventUseCase`) in the storage scope of its business. A
    provider that cannot confirm the payment yet, or cannot be asked, makes
    the job raise, and the queue tries again with backoff; a repeated run
    applies nothing twice (the order's notification keys).
    """

    def __init__(
        self,
        apply_payment_event: UseCaseContract[
            VerifiedPaymentEvent, PaymentWebhookReceipt
        ],
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._apply_payment_event: UseCaseContract[
            VerifiedPaymentEvent, PaymentWebhookReceipt
        ] = apply_payment_event
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: QueuedJobInput) -> PaymentWebhookReceipt:
        _, event = decode_payment_notification(input_data.payload, self._secret_cipher)
        return self._apply_payment_event.run(event)
