"""
A provider delivery taken all the way at once, for the billing tests: what
the webhook verifies (`read_notification`) applied as the queued job would
apply it (`ApplyPaymentEventUseCase`). The route itself only verifies and
queues (`ReceivePaymentWebhookUseCase`, tests/billing/test_queued_payment_webhooks.py).
"""

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.payments import (
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
    VerifiedPaymentEvent,
)


class SynchronousPaymentWebhook(
    UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
):
    def __init__(
        self,
        payment_gateway: PaymentGatewayAdapterContract,
        apply_event: UseCaseContract[VerifiedPaymentEvent, PaymentWebhookReceipt],
    ) -> None:
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._apply_event: UseCaseContract[
            VerifiedPaymentEvent, PaymentWebhookReceipt
        ] = apply_event

    def run(self, input_data: PaymentWebhookDelivery) -> PaymentWebhookReceipt:
        return self._apply_event.run(self._payment_gateway.read_notification(input_data))
