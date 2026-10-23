from app.contracts.billing import PaymentGatewayAdapterContract
from app.schemas.constants.payments import PaymentProvider
from app.schemas.dto.payment_retries import PaymentRetryRequest, PaymentRetryResult
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentWebhookDelivery,
    VerifiedPaymentEvent,
)
from app.schemas.typings.billing.strings import PaymentProviderReference


class PaymentGatewayRouterAdapter(PaymentGatewayAdapterContract):
    """
    The one payment gateway the use cases see: every call goes to the
    gateway of the provider it names (the checkout's provider, the
    endpoint a notification reached, the provider whose charges stop or
    retry), so a Flitt order is never sent to Stripe or the other way
    round.
    """

    def __init__(
        self,
        flitt_gateway: PaymentGatewayAdapterContract,
        stripe_gateway: PaymentGatewayAdapterContract,
    ) -> None:
        self._gateways: dict[PaymentProvider, PaymentGatewayAdapterContract] = {
            PaymentProvider.FLITT: flitt_gateway,
            PaymentProvider.STRIPE: stripe_gateway,
        }

    def create_checkout(
        self,
        request: PaymentCheckoutRequest,
    ) -> PaymentCheckoutSession:
        return self._gateways[request.provider].create_checkout(request)

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> VerifiedPaymentEvent:
        return self._gateways[delivery.provider].read_notification(delivery)

    def stop_recurring(
        self,
        provider: PaymentProvider,
        provider_reference: PaymentProviderReference,
    ) -> None:
        self._gateways[provider].stop_recurring(provider, provider_reference)

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        return self._gateways[request.provider].retry_charge(request)
