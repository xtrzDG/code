from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentNotification,
    PaymentWebhookDelivery,
)
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingPaymentGatewayAdapter(PaymentGatewayAdapterContract):
    """
    The payment provider (Flitt) behind its circuit breaker: while the
    circuit is open a checkout or a stop of automatic charges fails at once
    with ProviderCircuitOpenError (an ExternalServiceError, as when Flitt
    is unreachable) and makes no network call; timeouts and 5xx count
    against it. Notifications are verified locally and need no circuit.
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
    ) -> PaymentNotification:
        return self._inner_adapter.read_notification(delivery)

    def stop_recurring(self, provider_reference: PaymentProviderReference) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.stop_recurring(provider_reference),
        )
