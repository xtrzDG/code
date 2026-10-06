from typing import cast

import httpx

from app.clients.telegram.telegram_bot_calls import call_bot_api
from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.schemas.dto.channels.provider_profiles import (
    TelegramBotProfile,
    TelegramWebhookInfo,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
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
    TelegramCallbackQueryId,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.media.strings import ProviderMediaId
from app.utilities.channels.json_values import (
    JsonObject,
    as_object,
    read_identifier,
    read_integer,
    read_text,
)

TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS: float = 10.0
CALLBACK_QUERY_UPDATE: str = "callback_query"
# Customer messages and taps on the bot's inline buttons; edits and the
# rest are not handled.
ALLOWED_UPDATES: tuple[str, ...] = ("message", CALLBACK_QUERY_UPDATE)
TYPING_ACTION: str = "typing"
# Profile photos come in 160, 320 and 640 px squares; the smallest at least
# this wide is enough for an avatar in the cabinet.
AVATAR_MIN_WIDTH: int = 96


class TelegramBotClient(TelegramBotApiClientContract):
    """
    Minimal Telegram Bot API client (https://core.telegram.org/bots/api).

    The bot token is part of every request path, so it never appears in
    error messages and transport errors are not chained into them
    (`telegram_bot_calls`).
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
        reply_markup: JsonObject | None = None,
    ) -> ProviderMessageId | None:
        payload: JsonObject = {
            "chat_id": str(chat_id),
            "text": str(text),
            "link_preview_options": {"is_disabled": True},
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        sent: JsonObject | None = as_object(
            self._call(bot_token, "sendMessage", payload)
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

    def answer_callback_query(
        self, bot_token: ProviderToken, callback_query_id: TelegramCallbackQueryId
    ) -> None:
        self._call(
            bot_token,
            "answerCallbackQuery",
            {"callback_query_id": str(callback_query_id)},
        )

    def edit_message_text(
        self,
        bot_token: ProviderToken,
        message_id: ProviderMessageId,
        text: OutboundMessagePart,
    ) -> None:
        chat_id, _, number = str(message_id).rpartition(":")
        self._call(
            bot_token,
            "editMessageText",
            {
                "chat_id": chat_id,
                "message_id": int(number),
                "text": str(text),
                "link_preview_options": {"is_disabled": True},
            },
        )

    def get_webhook_info(self, bot_token: ProviderToken) -> TelegramWebhookInfo:
        result: JsonObject = (
            as_object(self._call(bot_token, "getWebhookInfo", {})) or {}
        )
        updates: list[object] = read_list(result, "allowed_updates")
        return TelegramWebhookInfo(
            url=read_webhook_url(result),
            # No list: Telegram's default, which includes button taps.
            receives_taps=not updates or CALLBACK_QUERY_UPDATE in updates,
        )

    def _call(
        self,
        bot_token: ProviderToken,
        method_name: str,
        payload: JsonObject,
    ) -> object:
        return call_bot_api(self._http_client, str(bot_token), method_name, payload)


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


def read_webhook_url(result: JsonObject) -> ChannelWebhookUrl | None:
    """getWebhookInfo's `url` ("" when the bot has no webhook)."""

    url: str | None = read_text(result, "url")
    try:
        return None if not url else ChannelWebhookUrl(url)
    except ValueError:
        return None
