from app.contracts.channel_clients import (
    JsonObject,
    ProviderToken,
    TelegramBotApiClientContract,
)
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.dto.channels.provider_profiles import (
    TelegramBotProfile,
    TelegramWebhookInfo,
)
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramBotUserId,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.strings import (
    OutboundMessagePart,
    ProviderMessageId,
    TelegramCallbackQueryId,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.media.strings import ProviderMediaId
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingTelegramBotAdapter(TelegramBotApiClientContract):
    """
    The Telegram Bot API behind one circuit breaker: the platform bot's
    (staff notifications and platform alerts) has its own circuit, so a
    flood of failing staff messages never blocks the businesses' bots, and
    the other way round. While the circuit is open every call fails at
    once with ProviderCircuitOpenError and makes no network call;
    timeouts and 5xx count against it, refusals (a blocked bot, a revoked
    token, a rate limit) do not.
    """

    def __init__(
        self,
        inner_client: TelegramBotApiClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_client: TelegramBotApiClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def get_me(self, bot_token: ProviderToken) -> TelegramBotProfile:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.get_me(bot_token),
        )

    def get_profile_photo_file_id(
        self, bot_token: ProviderToken, bot_user_id: TelegramBotUserId
    ) -> ProviderMediaId | None:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.get_profile_photo_file_id(
                bot_token, bot_user_id
            ),
        )

    def set_webhook(
        self,
        bot_token: ProviderToken,
        url: ChannelWebhookUrl,
        secret_token: TelegramWebhookSecret,
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.set_webhook(bot_token, url, secret_token),
        )

    def delete_webhook(self, bot_token: ProviderToken) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.delete_webhook(bot_token),
        )

    def send_message(
        self,
        bot_token: ProviderToken,
        chat_id: ChannelUserId,
        text: OutboundMessagePart,
        reply_markup: JsonObject | None = None,
    ) -> ProviderMessageId | None:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.send_message(
                bot_token, chat_id, text, reply_markup
            ),
        )

    def answer_callback_query(
        self, bot_token: ProviderToken, callback_query_id: TelegramCallbackQueryId
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.answer_callback_query(
                bot_token, callback_query_id
            ),
        )

    def edit_message_text(
        self,
        bot_token: ProviderToken,
        message_id: ProviderMessageId,
        text: OutboundMessagePart,
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.edit_message_text(bot_token, message_id, text),
        )

    def get_webhook_info(self, bot_token: ProviderToken) -> TelegramWebhookInfo:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.get_webhook_info(bot_token),
        )

    def send_typing_action(
        self, bot_token: ProviderToken, chat_id: ChannelUserId
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.send_typing_action(bot_token, chat_id),
        )
