from app.contracts.channels import ChannelAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundMessage,
    ChannelSendReceipt,
    ChannelWebhookPayload,
)
from app.schemas.typings.channels.strings import ChannelSecret, ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingChannelAdapter(ChannelAdapterContract):
    """
    A messaging channel behind its provider's circuit breaker (Meta for
    WhatsApp, Messenger and Instagram; Telegram for the businesses' bots).

    Sends and typing signals go through the circuit: while it is open they
    fail at once with ProviderCircuitOpenError and make no network call
    (the outbox tries the message again after the circuit's pause);
    timeouts, connection errors and 5xx count against it. Reading webhooks
    (signatures, payloads) and the best-effort tap acknowledgements need
    no circuit and go straight to the channel.
    """

    def __init__(
        self,
        inner_adapter: ChannelAdapterContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_adapter: ChannelAdapterContract = inner_adapter
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def verify_signature(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        self._inner_adapter.verify_signature(payload, channel_secret)

    def parse_webhook(
        self,
        payload: ChannelWebhookPayload,
    ) -> list[ChannelInboundMessage]:
        return self._inner_adapter.parse_webhook(payload)

    def split(
        self, text: MessageText, choices: ReplyChoices | None = None
    ) -> list[MessageText]:
        return self._inner_adapter.split(text, choices)

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
        choices: ReplyChoices | None = None,
    ) -> ChannelSendReceipt:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.send(target, text, choices),
        )

    def acknowledge_taps(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        self._inner_adapter.acknowledge_taps(payload, channel_secret)

    def signal_typing(
        self,
        target: ChannelDeliveryTarget,
        replying_to: ProviderMessageId | None,
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_adapter.signal_typing(target, replying_to),
        )
