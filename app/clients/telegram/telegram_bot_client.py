import httpx

from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramBotUsername,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.strings import OutboundMessagePart
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.channels.json_values import (
    JsonObject,
    as_object,
    parse_json_object,
    read_integer,
    read_text,
)

TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS: float = 10.0
# Telegram answers 401 or 404 when the token is wrong or revoked (getMe while
# connecting; any later call means the bot stopped working). 403 is about
# one chat (the customer blocked the bot), not the bot.
REJECTED_TOKEN_ERROR_CODES: frozenset[int] = frozenset({401, 404})
# Only customer messages are handled; edits, callbacks and the rest are not.
ALLOWED_UPDATES: tuple[str, ...] = ("message",)


class TelegramBotClient(TelegramBotApiClientContract):
    """
    Minimal Telegram Bot API client (https://core.telegram.org/bots/api).

    The bot token is part of every request path, so it never appears in
    error messages and transport errors are not chained into them.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        base_url: str = TELEGRAM_API_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def get_me(self, bot_token: ProviderToken) -> TelegramBotProfile:
        result: JsonObject | None = as_object(self._call(bot_token, "getMe", {}))
        username: str | None = None if result is None else read_text(result, "username")
        if username is None:
            raise ExternalServiceError("Telegram getMe returned no bot username.")

        try:
            return TelegramBotProfile(username=TelegramBotUsername(username))
        except ValueError as error:
            raise ExternalServiceError(
                "Telegram getMe returned an invalid bot username."
            ) from error

    def set_webhook(
        self,
        bot_token: ProviderToken,
        url: ChannelWebhookUrl,
        secret_token: TelegramWebhookSecret,
    ) -> None:
        self._call(
            bot_token,
            "setWebhook",
            {
                "url": str(url),
                "secret_token": str(secret_token),
                "allowed_updates": list(ALLOWED_UPDATES),
                "drop_pending_updates": False,
            },
        )

    def delete_webhook(self, bot_token: ProviderToken) -> None:
        self._call(bot_token, "deleteWebhook", {"drop_pending_updates": False})

    def send_message(
        self,
        bot_token: ProviderToken,
        chat_id: ChannelUserId,
        text: OutboundMessagePart,
    ) -> None:
        self._call(
            bot_token,
            "sendMessage",
            {
                "chat_id": str(chat_id),
                "text": str(text),
                "link_preview_options": {"is_disabled": True},
            },
        )

    def _call(
        self,
        bot_token: ProviderToken,
        method_name: str,
        payload: JsonObject,
    ) -> object:
        try:
            response: httpx.Response = self._http_client.post(
                f"/bot{bot_token}/{method_name}",
                json=payload,
            )
        except httpx.HTTPError as error:
            # Chaining would carry the request URL, which contains the token.
            raise ExternalServiceError(
                f"Telegram {method_name} failed: {type(error).__name__}."
            ) from None

        body: JsonObject | None = parse_json_object(response.content)
        if body is None:
            raise ExternalServiceError(
                f"Telegram {method_name} returned HTTP {response.status_code} "
                "without a JSON body."
            )

        if body.get("ok") is True:
            return body.get("result")

        error_code: int = read_integer(body, "error_code") or response.status_code
        description: str = read_text(body, "description") or "unknown error"
        if method_name == "getMe" and error_code in REJECTED_TOKEN_ERROR_CODES:
            raise ValidationFailedError(
                "Telegram rejected the bot token; copy it again from @BotFather."
            )

        if error_code in REJECTED_TOKEN_ERROR_CODES:
            raise ChannelCredentialRejectedError(
                f"Telegram {method_name} rejected the bot token ({error_code}: "
                f"{description})."
            )

        raise ExternalServiceError(
            f"Telegram {method_name} failed ({error_code}): {description}"
        )
