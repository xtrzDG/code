from typing import cast

import httpx

from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramBotUserId,
    TelegramBotUsername,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.strings import (
    OutboundMessagePart,
    ProviderMessageId,
    TelegramBotDisplayName,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.media.strings import ProviderMediaId
from app.utilities.channels.json_values import (
    JsonObject,
    as_object,
    parse_json_object,
    read_identifier,
    read_integer,
    read_object,
    read_text,
)
from app.utilities.channels.retry_after import read_retry_after_seconds

TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS: float = 10.0
# Telegram answers 401 or 404 when the token is wrong or revoked (getMe while
# connecting; any later call means the bot stopped working). 403 is about
# one chat (the customer blocked the bot), not the bot.
REJECTED_TOKEN_ERROR_CODES: frozenset[int] = frozenset({401, 404})
# "Too Many Requests: retry after N" (`parameters.retry_after`).
RATE_LIMITED_ERROR_CODE: int = 429
CLIENT_ERROR_CODES: range = range(400, 500)
# Only customer messages are handled; edits, callbacks and the rest are not.
ALLOWED_UPDATES: tuple[str, ...] = ("message",)
TYPING_ACTION: str = "typing"
# Profile photos come in 160, 320 and 640 px squares; the smallest at least
# this wide is enough for an avatar in the cabinet.
AVATAR_MIN_WIDTH: int = 96


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
        if result is None or username is None:
            raise ExternalServiceError("Telegram getMe returned no bot username.")

        try:
            return TelegramBotProfile(
                username=TelegramBotUsername(username),
                bot_user_id=read_bot_user_id(result),
                display_name=read_display_name(result),
            )
        except ValueError as error:
            raise ExternalServiceError(
                "Telegram getMe returned an invalid bot username."
            ) from error

    def get_profile_photo_file_id(
        self, bot_token: ProviderToken, bot_user_id: TelegramBotUserId
    ) -> ProviderMediaId | None:
        result: JsonObject | None = as_object(
            self._call(
                bot_token,
                "getUserProfilePhotos",
                {"user_id": int(str(bot_user_id)), "limit": 1},
            )
        )
        photos: list[object] = [] if result is None else read_list(result, "photos")
        return choose_avatar_size(as_objects(photos[0]) if photos else [])

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
    ) -> ProviderMessageId | None:
        sent: JsonObject | None = as_object(
            self._call(
                bot_token,
                "sendMessage",
                {
                    "chat_id": str(chat_id),
                    "text": str(text),
                    "link_preview_options": {"is_disabled": True},
                },
            )
        )
        message_id: str | None = (
            None if sent is None else read_identifier(sent, "message_id")
        )
        return (
            None if message_id is None else ProviderMessageId(f"{chat_id}:{message_id}")
        )

    def send_typing_action(
        self, bot_token: ProviderToken, chat_id: ChannelUserId
    ) -> None:
        self._call(
            bot_token,
            "sendChatAction",
            {"chat_id": str(chat_id), "action": TYPING_ACTION},
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

        if error_code == RATE_LIMITED_ERROR_CODE:
            parameters: JsonObject = read_object(body, "parameters") or {}
            raise ProviderRateLimitedError(
                f"Telegram {method_name} is rate limited: {description}",
                retry_after_seconds=read_retry_after_seconds(
                    read_integer(parameters, "retry_after"),
                    response.headers.get("Retry-After"),
                ),
            )

        if error_code in REJECTED_TOKEN_ERROR_CODES:
            raise ChannelCredentialRejectedError(
                f"Telegram {method_name} rejected the bot token ({error_code}: "
                f"{description})."
            )

        if CLIENT_ERROR_CODES.start <= error_code < CLIENT_ERROR_CODES.stop:
            # A refusal of this request (blocked bot, unknown chat, bad text):
            # sending it again cannot help.
            raise ProviderRejectedMessageError(
                f"Telegram {method_name} refused the request ({error_code}): "
                f"{description}"
            )

        raise ExternalServiceError(
            f"Telegram {method_name} failed ({error_code}): {description}"
        )


def read_bot_user_id(result: JsonObject) -> TelegramBotUserId | None:
    """getMe's numeric `id` as a typed id; None when it is missing or odd."""

    bot_id: int | None = read_integer(result, "id")
    if bot_id is None or bot_id <= 0:
        return None

    return TelegramBotUserId(str(bot_id))


def read_display_name(result: JsonObject) -> TelegramBotDisplayName | None:
    name: str | None = read_text(result, "first_name")
    return None if name is None or not name.strip() else TelegramBotDisplayName(name)


def read_list(source: JsonObject, key: str) -> list[object]:
    value: object = source.get(key)
    return list(cast(list[object], value)) if isinstance(value, list) else []


def as_objects(value: object) -> list[JsonObject]:
    items: list[object] = (
        list(cast(list[object], value)) if isinstance(value, list) else []
    )
    found: list[JsonObject] = []
    for item in items:
        item_object: JsonObject | None = as_object(item)
        if item_object is not None:
            found.append(item_object)
    return found


def choose_avatar_size(sizes: list[JsonObject]) -> ProviderMediaId | None:
    """
    The file of the smallest photo size at least `AVATAR_MIN_WIDTH` wide
    (Telegram lists them smallest first), else the largest one.
    """

    usable: list[tuple[int, str]] = []
    for size in sizes:
        file_id: str | None = read_text(size, "file_id")
        if file_id is not None:
            usable.append((read_integer(size, "width") or 0, file_id))

    if not usable:
        return None

    usable.sort(key=lambda entry: entry[0])
    for width, file_id in usable:
        if width >= AVATAR_MIN_WIDTH:
            return ProviderMediaId(file_id)

    return ProviderMediaId(usable[-1][1])
