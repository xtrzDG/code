from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingSmsSenderAdapter(SmsMessagingClientContract):
    """
    SMS (Twilio: staff notifications, missed-call text-backs) behind the
    Twilio circuit breaker: while it is open an SMS fails at once with
    ProviderCircuitOpenError and makes no network call; timeouts and 5xx
    count against the circuit, a refused number does not.
    """

    def __init__(
        self,
        inner_client: SmsMessagingClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_client: SmsMessagingClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.send_sms(recipient, text),
        )
