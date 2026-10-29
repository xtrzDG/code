from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.constants.payments import PaymentProvider
from app.schemas.dto.payment_retries import PaymentRetryRequest, PaymentRetryResult
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentWebhookDelivery,
    VerifiedPaymentEvent,
)
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingPaymentGatewayAdapter(PaymentGatewayAdapterContract):
    """
    One payment provider (Flitt or Stripe) behind its circuit breaker:
    while the circuit is open a checkout, a stop of automatic charges or a
    retry of a declined charge fails at once with ProviderCircuitOpenError
    (an ExternalServiceError, as when the provider is unreachable) and makes
    no network call; timeouts and 5xx count against it, a refusal or a
    declined card does not. Notifications are verified locally and need no
    circuit.
    """

    def __init__(
        self,
        inner_adapter: PaymentGatewayAdapterContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_adapter: PaymentGatewayAdapterContract = inner_adapter
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def create_checkout(
        self,
        request: PaymentCheckoutRequest,
    ) -> PaymentCheckoutSession:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.create_checkout(request),
        )

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> VerifiedPaymentEvent:
        return self._inner_adapter.read_notification(delivery)

    def stop_recurring(
        self,
        provider: PaymentProvider,
        provider_reference: PaymentProviderReference,
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.stop_recurring(provider, provider_reference),
        )

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.retry_charge(request),
        )
