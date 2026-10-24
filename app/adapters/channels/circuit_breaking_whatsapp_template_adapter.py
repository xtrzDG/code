from app.contracts.channels import WhatsAppTemplateAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import ChannelSecret, ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingWhatsAppTemplateAdapter(WhatsAppTemplateAdapterContract):
    """
    WhatsApp templates (customer messages outside the 24-hour window, staff
    notifications) behind Meta's circuit breaker: while it is open a
    template fails at once with ProviderCircuitOpenError and makes no
    network call; timeouts and 5xx count against the circuit, a refused
    template does not.
    """

    def __init__(
        self,
        inner_adapter: WhatsAppTemplateAdapterContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_adapter: WhatsAppTemplateAdapterContract = inner_adapter
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def send_template(
        self,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
        credential: ChannelSecret | None = None,
    ) -> ProviderMessageId | None:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.send_template(
                phone_number_id,
                recipient,
                template_name,
                language_code,
                body_parameters,
                credential,
            ),
        )
