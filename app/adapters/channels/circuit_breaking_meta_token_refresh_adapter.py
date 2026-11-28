from app.contracts.channel_credentials import MetaTokenRefreshClientContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingMetaTokenRefreshAdapter(MetaTokenRefreshClientContract):
    """
    The renewal of WhatsApp Embedded Signup tokens behind Meta's circuit
    breaker: while it is open a renewal fails at once with
    ProviderCircuitOpenError and makes no network call (the next run tries
    again); timeouts and 5xx count against the circuit, a refused token or
    a request to slow down does not. Circuits live in one process, so the
    batch worker's renewals never stop the customer sends of another one.
    """

    def __init__(
        self,
        inner_client: MetaTokenRefreshClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_client: MetaTokenRefreshClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def refresh_business_token(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaAccessToken:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.refresh_business_token(token, app),
        )
