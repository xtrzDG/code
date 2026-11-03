from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import (
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
    VerifiedPaymentEvent,
)
from app.schemas.typings.billing.strings import PaymentNotificationKey
from app.use_cases.billing.payment_webhook.card_on_file_recording import (
    build_card_notice_key,
)
from app.use_cases.billing.payment_webhook.payment_notification_jobs import (
    APPLY_PAYMENT_NOTIFICATION_JOB,
    encode_payment_notification,
    payment_order_serial_key,
)
from app.use_cases.billing.payment_webhook.payment_order_lookup import (
    find_event_order,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    build_notification_key,
)


class ReceivePaymentWebhookUseCase(
    UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
):
    """
    A payment provider's notification (POST /v1/payments/flitt/webhook and
    POST /v1/payments/stripe/webhook), answered fast (API-03): the
    signature is verified and the event decoded (`read_notification`), its
    payment order looked up, and the event queued for a worker
    (`apply_payment_notification`, QUEUED). The queued job is the durable
    record of the delivery: it is stored before the answer, so a delivery
    the provider was told about is never lost, and the job applies it with
    retries (the provider's status read back, the order's notification
    lock and keys: `ApplyPaymentEventUseCase`). The jobs of one order run
    one at a time in the order they arrived.

    A delivery whose notification the order applied already is a
    DUPLICATE and queues nothing; one that names no order of the platform
    is NotFoundError (the provider sends it again), and one the platform
    does not act on is IGNORED.
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        payment_order_repo: PaymentOrderRepoContract,
        job_queue: JobQueueFacilitatorContract,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: PaymentWebhookDelivery) -> PaymentWebhookReceipt:
        event: VerifiedPaymentEvent = self._payment_gateway.read_notification(
            input_data
        )
        payment_order: PaymentOrderDocument | None = find_event_order(
            self._payment_order_repo, event
        )
        if payment_order is None:
            return PaymentWebhookReceipt(outcome=PaymentWebhookOutcome.IGNORED)

        if not has_news(event, payment_order.processed_notification_keys):
            return PaymentWebhookReceipt(
                outcome=PaymentWebhookOutcome.DUPLICATE,
                payment_order_id=payment_order.id,
            )

        self._job_queue.enqueue(
            APPLY_PAYMENT_NOTIFICATION_JOB,
            encode_payment_notification(payment_order.id, event, self._secret_cipher),
            payment_order.business_id,
            serial_key=payment_order_serial_key(payment_order.id),
        )
        return PaymentWebhookReceipt(
            outcome=PaymentWebhookOutcome.QUEUED, payment_order_id=payment_order.id
        )


def has_news(
    event: VerifiedPaymentEvent, processed: list[PaymentNotificationKey]
) -> bool:
    """The event holds a payment status or a saved card the order has not applied."""

    keys: list[PaymentNotificationKey] = []
    if event.payment is not None:
        keys.append(build_notification_key(event.payment))
    if event.payment_method is not None:
        keys.append(build_card_notice_key(event.payment_method))

    return any(key not in processed for key in keys)
